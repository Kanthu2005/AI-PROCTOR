import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus
from app.models.assessment import Assessment, SectionQuestion
from app.models.candidate import CandidateInvitation
from app.schemas.analytics import AssessmentAnalyticsResponse, CandidateRankItem, QuestionAnalyticsItem


class AnalyticsService:
    @staticmethod
    def compute_rankings_and_percentiles(db: Session, assessment_id: str) -> List[Attempt]:
        """
        Computes official rankings and percentiles with tie-breakers:
        1. Higher score
        2. Higher accuracy percentage
        3. Less time taken
        4. Earlier submission timestamp
        """
        attempts = db.query(Attempt).filter(
            Attempt.assessment_id == assessment_id,
            Attempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED])
        ).all()

        if not attempts:
            return []

        attempt_stats = []
        for att in attempts:
            # Time taken in seconds
            time_taken = 0
            if att.started_at and att.submitted_at:
                t_diff = (att.submitted_at - att.started_at).total_seconds()
                time_taken = max(1, int(t_diff))

            # Accuracy calculation
            answers = att.answers
            total_answered = len(answers)
            correct_answered = sum(1 for a in answers if a.is_correct is True)
            accuracy = (correct_answered / total_answered * 100.0) if total_answered > 0 else 0.0

            attempt_stats.append({
                "attempt": att,
                "score": att.total_score,
                "accuracy": accuracy,
                "time_taken": time_taken,
                "submitted_at": att.submitted_at or datetime.now(timezone.utc)
            })

        # Sort using compound tie-breaker key
        attempt_stats.sort(
            key=lambda x: (
                -x["score"],          # 1. Higher score first
                -x["accuracy"],       # 2. Higher accuracy first
                x["time_taken"],      # 3. Faster completion first
                x["submitted_at"]     # 4. Earlier submission timestamp first
            )
        )

        total_candidates = len(attempt_stats)

        # Assign ranks and percentiles
        for idx, item in enumerate(attempt_stats):
            rank = idx + 1
            att = item["attempt"]
            att.rank = rank

            # Percentile formula: proportion of cohort scoring at or below candidate
            scores_at_or_below = sum(1 for other in attempt_stats if other["score"] <= item["score"])
            percentile = round((scores_at_or_below / total_candidates) * 100.0, 2)
            att.percentile = percentile

        db.commit()
        return [item["attempt"] for item in attempt_stats]

    @staticmethod
    def get_assessment_analytics(db: Session, assessment_id: str) -> AssessmentAnalyticsResponse:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Run fresh rankings calculation
        ranked_attempts = AnalyticsService.compute_rankings_and_percentiles(db, assessment_id)

        total_invited = db.query(CandidateInvitation).filter(CandidateInvitation.assessment_id == assessment_id).count()
        total_started = db.query(Attempt).filter(Attempt.assessment_id == assessment_id).count()
        completed_attempts = [a for a in ranked_attempts]
        total_completed = len(completed_attempts)
        total_passed = sum(1 for a in completed_attempts if a.is_passed)

        pass_pct = round((total_passed / total_completed * 100.0), 2) if total_completed > 0 else 0.0
        scores = [a.total_score for a in completed_attempts] if completed_attempts else [0.0]

        avg_score = round(statistics.mean(scores), 2) if scores else 0.0
        median_score = round(statistics.median(scores), 2) if scores else 0.0
        highest_score = max(scores) if scores else 0.0
        lowest_score = min(scores) if scores else 0.0

        # Build Leaderboard
        leaderboard = []
        for att in ranked_attempts:
            time_taken = 0
            if att.started_at and att.submitted_at:
                time_taken = max(1, int((att.submitted_at - att.started_at).total_seconds()))

            answers = att.answers
            tot_ans = len(answers)
            cor_ans = sum(1 for a in answers if a.is_correct is True)
            accuracy = round((cor_ans / tot_ans * 100.0), 2) if tot_ans > 0 else 0.0

            leaderboard.append(CandidateRankItem(
                attempt_id=att.id,
                candidate_name=att.candidate_name,
                candidate_email=att.candidate_email,
                score=att.total_score,
                percentage=att.percentage,
                is_passed=att.is_passed,
                rank=att.rank or 0,
                percentile=att.percentile or 0.0,
                time_taken_seconds=time_taken,
                accuracy_percentage=accuracy,
                risk_level=att.risk_level.value,
                submitted_at=att.submitted_at
            ))

        # Build Question-level analytics
        all_sq = db.query(SectionQuestion).join(SectionQuestion.section).filter(
            SectionQuestion.section.has(assessment_id=assessment.id)
        ).all()

        question_analytics = []
        for sq in all_sq:
            qv = sq.question_version
            answers = db.query(AttemptAnswer).filter(
                AttemptAnswer.question_version_id == qv.id
            ).all()

            total_q_attempts = len(answers)
            correct_q_attempts = sum(1 for a in answers if a.is_correct is True)
            pass_rate = round((correct_q_attempts / total_q_attempts * 100.0), 2) if total_q_attempts > 0 else 0.0
            avg_time = round(statistics.mean([a.time_spent_seconds for a in answers]), 1) if answers else 0.0

            # Discrimination index: accuracy difference between top 27% and bottom 27%
            disc_idx = 0.0
            if len(ranked_attempts) >= 4:
                k = max(1, int(len(ranked_attempts) * 0.27))
                top_group_ids = {a.id for a in ranked_attempts[:k]}
                bot_group_ids = {a.id for a in ranked_attempts[-k:]}

                top_correct = sum(1 for a in answers if a.attempt_id in top_group_ids and a.is_correct is True)
                bot_correct = sum(1 for a in answers if a.attempt_id in bot_group_ids and a.is_correct is True)

                top_acc = (top_correct / k) if k > 0 else 0.0
                bot_acc = (bot_correct / k) if k > 0 else 0.0
                disc_idx = round(top_acc - bot_acc, 2)

            question_analytics.append(QuestionAnalyticsItem(
                question_id=sq.question_id,
                title=qv.title,
                question_type=qv.question_type.value,
                total_attempts=total_q_attempts,
                correct_attempts=correct_q_attempts,
                pass_rate_percentage=pass_rate,
                avg_time_spent_seconds=avg_time,
                discrimination_index=disc_idx
            ))

        # Score distribution buckets (percentage ranges)
        score_distribution = {
            "0-20%": 0,
            "21-40%": 0,
            "41-60%": 0,
            "61-80%": 0,
            "81-100%": 0
        }
        for att in completed_attempts:
            pct = att.percentage or 0.0
            if pct <= 20.0:
                score_distribution["0-20%"] += 1
            elif pct <= 40.0:
                score_distribution["21-40%"] += 1
            elif pct <= 60.0:
                score_distribution["41-60%"] += 1
            elif pct <= 80.0:
                score_distribution["61-80%"] += 1
            else:
                score_distribution["81-100%"] += 1

        return AssessmentAnalyticsResponse(
            assessment_id=assessment.id,
            assessment_title=assessment.title,
            total_candidates_invited=total_invited,
            total_attempts_started=total_started,
            total_completed=total_completed,
            total_passed=total_passed,
            overall_pass_percentage=pass_pct,
            average_score=avg_score,
            median_score=median_score,
            highest_score=highest_score,
            lowest_score=lowest_score,
            leaderboard=leaderboard,
            question_analytics=question_analytics,
            score_distribution=score_distribution
        )

    @staticmethod
    def get_recruiter_dashboard_metrics(db: Session, org_id: str) -> Dict[str, Any]:
        """
        Computes real-time recruiter dashboard metrics for the organization:
        - Overall assessment counts & status breakdown (DRAFT, PUBLISHED, SCHEDULED, LIVE, CLOSED)
        - Candidate metrics (total invited, started, completed, passed, in-progress)
        - Alerts / flagged incidents count
        - Recent assessments list with candidate counts and completion rates
        - Real activities timeline
        - Active candidates currently in progress
        """
        now_utc = datetime.now(timezone.utc)

        # 1. Assessments
        assessments = db.query(Assessment).filter(Assessment.org_id == org_id).order_by(Assessment.created_at.desc()).all()
        total_assessments = len(assessments)

        status_counts = {
            "DRAFT": 0,
            "PUBLISHED": 0,
            "SCHEDULED": 0,
            "LIVE": 0,
            "CLOSED": 0
        }
        for a in assessments:
            if a.status and a.status.value in status_counts:
                status_counts[a.status.value] += 1

        # 2. Candidate Invitations & Attempts
        invitations = db.query(CandidateInvitation).filter(CandidateInvitation.org_id == org_id).all()
        total_candidates = len(invitations)

        assessment_ids = [a.id for a in assessments]
        all_attempts = db.query(Attempt).filter(Attempt.assessment_id.in_(assessment_ids)).all() if assessment_ids else []

        completed_attempts = [att for att in all_attempts if att.status in (AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED)]
        in_progress_attempts = [att for att in all_attempts if att.status == AttemptStatus.IN_PROGRESS]
        passed_attempts = [att for att in completed_attempts if att.is_passed]

        total_completed = len(completed_attempts)
        total_in_progress = len(in_progress_attempts)
        total_passed = len(passed_attempts)

        high_risk_attempts = [att for att in all_attempts if att.risk_level.value == "HIGH" or (att.risk_score and att.risk_score >= 40.0)]
        alerts_count = len(high_risk_attempts)

        # 3. Recent Assessments Table
        recent_assessments = []
        for a in assessments[:6]:
            q_count = sum(len(s.section_questions) for s in a.sections)
            a_invitations = [i for i in invitations if i.assessment_id == a.id]
            a_attempts = [att for att in all_attempts if att.assessment_id == a.id]
            a_completed = [att for att in a_attempts if att.status in (AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED)]

            inv_count = len(a_invitations)
            comp_count = len(a_completed)
            completion_rate = round((comp_count / inv_count * 100), 1) if inv_count > 0 else 0

            rep_token = a_invitations[0].invitation_token if a_invitations else None

            recent_assessments.append({
                "id": a.id,
                "title": a.title,
                "status": a.status.value if a.status else "DRAFT",
                "total_duration_minutes": a.total_duration_minutes,
                "total_marks": a.total_marks,
                "question_count": q_count,
                "candidates_invited": inv_count,
                "candidates_completed": comp_count,
                "completion_rate": completion_rate,
                "sample_token": rep_token,
                "created_at": a.created_at.isoformat() if a.created_at else None
            })

        # 4. Recent Activities Feed
        activities = []
        for att in sorted(completed_attempts, key=lambda x: x.submitted_at or x.created_at, reverse=True)[:5]:
            ass_title = next((a.title for a in assessments if a.id == att.assessment_id), "Assessment")
            activities.append({
                "user": att.candidate_name,
                "action": "submitted the assessment",
                "context": ass_title,
                "time": att.submitted_at.isoformat() if att.submitted_at else att.created_at.isoformat(),
                "type": "submission",
                "isAlert": False
            })

        for att in sorted(in_progress_attempts, key=lambda x: x.started_at or x.created_at, reverse=True)[:5]:
            ass_title = next((a.title for a in assessments if a.id == att.assessment_id), "Assessment")
            activities.append({
                "user": att.candidate_name,
                "action": "started the assessment",
                "context": ass_title,
                "time": att.started_at.isoformat() if att.started_at else att.created_at.isoformat(),
                "type": "started",
                "isAlert": False
            })

        for att in high_risk_attempts[:3]:
            ass_title = next((a.title for a in assessments if a.id == att.assessment_id), "Assessment")
            activities.append({
                "user": f"Security Alert: {att.candidate_name}",
                "action": f"Elevated proctoring risk flagged ({att.risk_score} pts)",
                "context": ass_title,
                "time": att.started_at.isoformat() if att.started_at else att.created_at.isoformat(),
                "type": "alert",
                "isAlert": True
            })

        for inv in sorted(invitations, key=lambda x: x.created_at, reverse=True)[:3]:
            activities.append({
                "user": inv.full_name,
                "action": "was invited to assessment",
                "context": inv.email,
                "time": inv.created_at.isoformat() if inv.created_at else None,
                "type": "invite",
                "isAlert": False
            })

        activities.sort(key=lambda x: x.get("time") or "", reverse=True)
        activities = activities[:10]

        # 5. Active Candidates
        active_candidates = []
        for att in in_progress_attempts[:6]:
            ass = next((a for a in assessments if a.id == att.assessment_id), None)
            total_q = sum(len(s.section_questions) for s in ass.sections) if ass else 0
            answered_q = len(att.answers) if att.answers else 0

            time_elapsed_str = ""
            if att.started_at:
                start_utc = att.started_at.replace(tzinfo=timezone.utc) if att.started_at.tzinfo is None else att.started_at
                mins = max(1, int((now_utc - start_utc).total_seconds() // 60))
                time_elapsed_str = f"{mins}m elapsed"

            active_candidates.append({
                "name": att.candidate_name,
                "email": att.candidate_email,
                "assessment_title": ass.title if ass else "Assessment",
                "progress": f"Q{answered_q} / {total_q} • {time_elapsed_str}",
                "risk": att.risk_level.value if att.risk_level else "LOW",
                "risk_score": att.risk_score or 0.0,
                "attempt_id": att.id
            })

        return {
            "total_assessments": total_assessments,
            "status_counts": status_counts,
            "total_candidates": total_candidates,
            "total_completed": total_completed,
            "total_in_progress": total_in_progress,
            "total_passed": total_passed,
            "pass_rate": round((total_passed / total_completed * 100), 1) if total_completed > 0 else 0.0,
            "alerts_count": alerts_count,
            "recent_assessments": recent_assessments,
            "activities": activities,
            "active_candidates": active_candidates
        }
