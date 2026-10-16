import io
import csv
import json
import math
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.responses import Response

from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus
from app.models.assessment import Assessment, Section, SectionQuestion, AssessmentRule
from app.models.question import QuestionVersion, QuestionType
from app.models.user import User, Role
from app.services.sandbox_service import CodingSandboxRunner
from app.services.audit_service import AuditService


class EvaluationService:
    @staticmethod
    def evaluate_mcq(
        selected_option_ids: List[str],
        correct_option_ids: List[str],
        positive_marks: float,
        negative_marks: float,
        negative_marking_enabled: bool = True,
        multiple_select_policy: str = "PARTIAL_WITH_PENALTY",
        is_multiple_select: bool = False
    ) -> Tuple[bool, float]:
        """
        Deterministic MCQ scoring engine:
        - Unanswered questions always receive 0.0 marks (never penalized).
        - Single-select: exact match gives positive_marks; incorrect gives -negative_marks (if enabled).
        - Multiple-select policies:
            * ALL_OR_NOTHING: exact match gives positive_marks; any mistake gives -negative_marks.
            * PARTIAL_WITH_PENALTY: proportional positive marks for true positives,
              deduction for false positives, bounded between [-negative_marks, positive_marks].
        - Deterministically rounded to 2 decimal places.
        """
        # Unanswered Policy
        if not selected_option_ids:
            return False, 0.0

        correct_set = set(correct_option_ids)
        selected_set = set(selected_option_ids)

        # Single select question scoring
        if not is_multiple_select:
            is_correct = (selected_set == correct_set)
            if is_correct:
                return True, round(float(positive_marks), 2)
            else:
                deduction = float(negative_marks) if negative_marking_enabled else 0.0
                return False, round(-deduction, 2)

        # Multiple-select question scoring
        if selected_set == correct_set:
            return True, round(float(positive_marks), 2)

        if multiple_select_policy == "ALL_OR_NOTHING":
            deduction = float(negative_marks) if negative_marking_enabled else 0.0
            return False, round(-deduction, 2)

        # PARTIAL_WITH_PENALTY policy
        total_correct_options = len(correct_set)
        if total_correct_options == 0:
            return False, 0.0

        true_positives = len(selected_set.intersection(correct_set))
        false_positives = len(selected_set.difference(correct_set))

        # Partial credit earned
        earned_ratio = true_positives / total_correct_options
        score = earned_ratio * float(positive_marks)

        # Penalty for incorrectly selected options
        if false_positives > 0 and negative_marking_enabled:
            penalty_per_option = float(negative_marks) if float(negative_marks) > 0 else (float(positive_marks) / total_correct_options)
            score -= (false_positives * penalty_per_option)

        if negative_marking_enabled:
            min_bound = -float(negative_marks) if float(negative_marks) > 0 else 0.0
            score = max(min_bound, min(float(positive_marks), score))
        else:
            score = max(0.0, min(float(positive_marks), score))

        return False, round(score, 2)

    @staticmethod
    def evaluate_fill_in_blank(
        text_response: Optional[str],
        accepted_answers: List[str],
        positive_marks: float,
        negative_marks: float,
        negative_marking_enabled: bool = True
    ) -> Tuple[bool, float]:
        """
        Evaluates fill-in-the-blank questions case-insensitively.
        Unanswered receives 0.0.
        """
        if not text_response or not text_response.strip():
            return False, 0.0

        cand_clean = text_response.strip().lower()
        accepted_clean = [a.strip().lower() for a in accepted_answers if a and a.strip()]

        if cand_clean in accepted_clean:
            return True, round(float(positive_marks), 2)
        else:
            deduction = float(negative_marks) if negative_marking_enabled else 0.0
            return False, round(-deduction, 2)

    @staticmethod
    def evaluate_coding_question(
        code_response: Optional[str],
        test_cases: List[Dict[str, Any]],
        positive_marks: float
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Server-side trusted code evaluation using CodingSandboxRunner.
        Never trusts client-submitted test results or scores.
        """
        code = (code_response or "").strip()
        if not code or not test_cases:
            return False, 0.0, {"error": "Empty code response or no test cases provided"}

        exec_res = CodingSandboxRunner.execute_code(code, test_cases)
        passed_tc = exec_res.get("passed_test_cases", 0)
        total_tc = exec_res.get("total_test_cases", len(test_cases))

        ratio = (passed_tc / total_tc) if total_tc > 0 else 0.0
        score = round(ratio * float(positive_marks), 2)
        is_correct = (passed_tc == total_tc and total_tc > 0)

        return is_correct, score, exec_res

    @staticmethod
    def evaluate_attempt(
        db: Session,
        attempt_id: str,
        recompute_all: bool = False
    ) -> Attempt:
        """
        Authoritative server-side evaluation of candidate attempt:
        - Evaluates questions deterministically
        - Computes section-level breakdowns, cut-offs, totals, and pass/fail rules
        - Preserves manual descriptive grading unless recompute_all is specified
        - Prevents duplicate evaluations
        """
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        # Prevent duplicate evaluations if already fully evaluated
        if attempt.evaluation_status == "FULLY_EVALUATED" and not recompute_all:
            return attempt

        assessment = attempt.assessment
        rules = assessment.rules
        neg_marking_enabled = rules.negative_marking_enabled if rules else True
        mult_select_policy = rules.multiple_select_policy if rules and hasattr(rules, 'multiple_select_policy') else "PARTIAL_WITH_PENALTY"

        # Load section questions
        all_sq = db.query(SectionQuestion).join(SectionQuestion.section).filter(
            SectionQuestion.section.has(assessment_id=assessment.id)
        ).all()

        answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt_id).all()
        answers_by_version = {a.question_version_id: a for a in answers}

        has_pending_descriptive = False

        for sq in all_sq:
            ans = answers_by_version.get(sq.question_version_id)
            qv = sq.question_version

            if not ans:
                continue

            # 1. MCQ Single / True-False
            if qv.question_type in [QuestionType.MCQ_SINGLE, QuestionType.TRUE_FALSE]:
                correct_ids = [opt["id"] for opt in qv.options if opt.get("is_correct")]
                is_correct, score = EvaluationService.evaluate_mcq(
                    selected_option_ids=ans.selected_option_ids or [],
                    correct_option_ids=correct_ids,
                    positive_marks=sq.positive_marks,
                    negative_marks=sq.negative_marks,
                    negative_marking_enabled=neg_marking_enabled,
                    is_multiple_select=False
                )
                ans.is_correct = is_correct
                ans.marks_awarded = score

            # 2. MCQ Multiple-Select
            elif qv.question_type == QuestionType.MCQ_MULTIPLE:
                correct_ids = [opt["id"] for opt in qv.options if opt.get("is_correct")]
                is_correct, score = EvaluationService.evaluate_mcq(
                    selected_option_ids=ans.selected_option_ids or [],
                    correct_option_ids=correct_ids,
                    positive_marks=sq.positive_marks,
                    negative_marks=sq.negative_marks,
                    negative_marking_enabled=neg_marking_enabled,
                    multiple_select_policy=mult_select_policy,
                    is_multiple_select=True
                )
                ans.is_correct = is_correct
                ans.marks_awarded = score

            # 3. Fill in the Blank
            elif qv.question_type == QuestionType.FILL_IN_BLANK:
                accepted = [
                    opt.get("text", "") for opt in (qv.options or []) if opt.get("is_correct", True)
                ]
                if qv.explanation and qv.explanation.strip():
                    accepted.append(qv.explanation.strip())

                is_correct, score = EvaluationService.evaluate_fill_in_blank(
                    text_response=ans.text_response,
                    accepted_answers=accepted,
                    positive_marks=sq.positive_marks,
                    negative_marks=sq.negative_marks,
                    negative_marking_enabled=neg_marking_enabled
                )
                ans.is_correct = is_correct
                ans.marks_awarded = score

            # 4. Coding Questions
            elif qv.question_type == QuestionType.CODING:
                test_cases = qv.coding_details.get("test_cases", [])
                is_correct, score, exec_res = EvaluationService.evaluate_coding_question(
                    code_response=ans.code_response,
                    test_cases=test_cases,
                    positive_marks=sq.positive_marks
                )
                ans.is_correct = is_correct
                ans.marks_awarded = score
                ans.execution_result = exec_res

            # 5. SQL Questions
            elif qv.question_type == QuestionType.SQL:
                sol = qv.sql_details.get("solution_sql", "").strip().lower()
                cand_sql = (ans.code_response or "").strip().lower()
                if sol and cand_sql and sol == cand_sql:
                    ans.is_correct = True
                    ans.marks_awarded = round(float(sq.positive_marks), 2)
                elif cand_sql:
                    ans.is_correct = False
                    ans.marks_awarded = 0.0
                else:
                    ans.is_correct = False
                    ans.marks_awarded = 0.0

            # 6. Descriptive / Short Answer
            elif qv.question_type in [QuestionType.DESCRIPTIVE, QuestionType.SHORT_ANSWER]:
                if not ans.is_manually_evaluated:
                    ans.marks_awarded = 0.0
                    ans.is_correct = None
                    has_pending_descriptive = True

        db.commit()

        # Recalculate totals and section breakdown
        return EvaluationService.recalculate_attempt_totals(db, attempt, has_pending_descriptive)

    @staticmethod
    def recalculate_attempt_totals(
        db: Session,
        attempt: Attempt,
        has_pending_descriptive: bool = False
    ) -> Attempt:
        """
        Computes section scores, totals, percentages, and pass/fail rules.
        """
        assessment = attempt.assessment
        all_sq = db.query(SectionQuestion).join(SectionQuestion.section).filter(
            SectionQuestion.section.has(assessment_id=assessment.id)
        ).all()

        answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
        answers_by_version = {a.question_version_id: a for a in answers}

        # Group by section
        section_map = {}
        total_max_marks = 0.0

        for sq in all_sq:
            sec_id = sq.section_id
            if sec_id not in section_map:
                sec = sq.section
                section_map[sec_id] = {
                    "section_id": sec.id,
                    "title": sec.title,
                    "cut_off_marks": float(sec.cut_off_marks or 0.0),
                    "score": 0.0,
                    "max_marks": 0.0,
                    "is_passed": True,
                    "questions_count": 0,
                    "answered_count": 0
                }

            section_map[sec_id]["max_marks"] += float(sq.positive_marks)
            total_max_marks += float(sq.positive_marks)
            section_map[sec_id]["questions_count"] += 1

            ans = answers_by_version.get(sq.question_version_id)
            if ans:
                section_map[sec_id]["score"] += float(ans.marks_awarded)
                if ans.selected_option_ids or (ans.text_response and ans.text_response.strip()) or (ans.code_response and ans.code_response.strip()):
                    section_map[sec_id]["answered_count"] += 1

        total_score = 0.0
        all_sections_passed = True

        for sec_id, data in section_map.items():
            # Bounded section score
            data["score"] = round(max(0.0, data["score"]), 2)
            data["is_passed"] = (data["score"] >= data["cut_off_marks"])
            if not data["is_passed"]:
                all_sections_passed = False
            total_score += data["score"]

        total_score = round(max(0.0, total_score), 2)
        percentage = round((total_score / total_max_marks * 100.0), 2) if total_max_marks > 0 else 0.0
        overall_passed = (percentage >= float(assessment.passing_percentage)) and all_sections_passed

        attempt.total_score = total_score
        attempt.total_max_marks = round(total_max_marks, 2)
        attempt.percentage = percentage
        attempt.is_passed = overall_passed
        attempt.section_scores = section_map

        if has_pending_descriptive:
            attempt.evaluation_status = "REQUIRES_MANUAL_REVIEW"
        else:
            attempt.evaluation_status = "FULLY_EVALUATED"

        db.commit()
        db.refresh(attempt)
        return attempt

    @staticmethod
    def manual_evaluate_answer(
        db: Session,
        attempt_id: str,
        question_id: str,
        marks_awarded: float,
        reviewer_comments: Optional[str] = None,
        reviewer: Optional[User] = None
    ) -> AttemptAnswer:
        """
        Manual evaluation of descriptive/short answer question by recruiter:
        - Validates marks bounded by question positive marks
        - Updates answer record
        - Records immutable audit trail
        - Recalculates attempt totals and cohort rankings
        """
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        ans = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt_id,
            AttemptAnswer.question_id == question_id
        ).first()

        if not ans:
            raise HTTPException(status_code=404, detail="Answer not found for specified question")

        # Find question version to know positive marks
        sq = db.query(SectionQuestion).filter(
            SectionQuestion.question_version_id == ans.question_version_id
        ).first()
        max_marks = float(sq.positive_marks) if sq else 10.0

        if marks_awarded < 0.0 or marks_awarded > max_marks:
            raise HTTPException(
                status_code=400,
                detail=f"Awarded marks ({marks_awarded}) must be between 0.0 and {max_marks}"
            )

        old_marks = ans.marks_awarded
        ans.marks_awarded = round(float(marks_awarded), 2)
        ans.is_correct = (marks_awarded >= (max_marks * 0.5))
        ans.reviewer_comments = reviewer_comments
        ans.is_manually_evaluated = True
        ans.evaluated_at = datetime.now(timezone.utc)
        if reviewer:
            ans.evaluated_by_id = reviewer.id

        db.commit()

        # Audit trail for score modification
        AuditService.log_event(
            db,
            event_type="MANUAL_EVALUATION_MODIFIED",
            user_id=reviewer.id if reviewer else None,
            email=reviewer.email if reviewer else None,
            org_id=attempt.assessment.org_id if attempt.assessment else None,
            details={
                "attempt_id": attempt.id,
                "question_id": question_id,
                "old_marks": old_marks,
                "new_marks": ans.marks_awarded,
                "reviewer_comments": reviewer_comments
            }
        )

        # Check if other descriptive questions remain unevaluated
        unevaluated_descriptive_count = (
            db.query(AttemptAnswer)
            .join(SectionQuestion, SectionQuestion.question_version_id == AttemptAnswer.question_version_id)
            .join(QuestionVersion, QuestionVersion.id == SectionQuestion.question_version_id)
            .filter(
                AttemptAnswer.attempt_id == attempt_id,
                QuestionVersion.question_type.in_([QuestionType.DESCRIPTIVE, QuestionType.SHORT_ANSWER]),
                AttemptAnswer.is_manually_evaluated == False
            )
            .count()
        )

        # Recalculate totals
        EvaluationService.recalculate_attempt_totals(db, attempt, has_pending_descriptive=(unevaluated_descriptive_count > 0))

        # Recompute cohort rankings
        from app.services.analytics_service import AnalyticsService
        AnalyticsService.compute_rankings_and_percentiles(db, attempt.assessment_id)

        db.refresh(ans)
        return ans

    @staticmethod
    def suggest_descriptive_score(
        db: Session,
        attempt_id: str,
        question_id: str
    ) -> Dict[str, Any]:
        """
        Optional AI-suggested descriptive evaluation:
        - Analyzes text response against question explanation / rubric
        - Generates suggested score, rationale, and confidence
        - NEVER automatically commits score to the database without human confirmation
        """
        ans = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt_id,
            AttemptAnswer.question_id == question_id
        ).first()

        if not ans:
            raise HTTPException(status_code=404, detail="Answer not found for specified question")

        sq = db.query(SectionQuestion).filter(
            SectionQuestion.question_version_id == ans.question_version_id
        ).first()
        max_marks = float(sq.positive_marks) if sq else 10.0

        qv = db.query(QuestionVersion).filter(QuestionVersion.id == ans.question_version_id).first()
        # Heuristic / semantic analysis
        response_text = (ans.text_response or "").strip()
        if not response_text:
            return {
                "question_id": question_id,
                "suggested_marks": 0.0,
                "max_marks": max_marks,
                "confidence": 1.0,
                "rationale": "Candidate provided no response.",
                "requires_human_confirmation": True
            }

        # Analyze key technical terms
        word_count = len(response_text.split())
        rubric_text = (qv.explanation if qv else "") or "technical completeness clarity concepts"
        keywords = [k.lower() for k in rubric_text.split() if len(k) > 4]
        matches = sum(1 for kw in keywords if kw in response_text.lower())

        base_ratio = min(1.0, (matches / max(1, len(keywords)) * 0.7) + (min(word_count, 80) / 80.0 * 0.3))
        suggested_marks = round(base_ratio * max_marks, 2)
        confidence = round(min(0.95, 0.60 + (matches * 0.08)), 2)
        rationale = f"Detected {matches} relevant key concepts from evaluation rubric with {word_count} words explanation."

        # Cache suggestion on AttemptAnswer model without altering official marks
        ans.ai_suggested_marks = suggested_marks
        ans.ai_suggestion_rationale = rationale
        ans.ai_suggestion_confidence = confidence
        db.commit()

        return {
            "question_id": question_id,
            "suggested_marks": suggested_marks,
            "max_marks": max_marks,
            "confidence": confidence,
            "rationale": rationale,
            "requires_human_confirmation": True
        }

    @staticmethod
    def generate_pdf_document(title: str, subtitle: str, headers: List[str], rows: List[List[str]]) -> bytes:
        """
        Pure-python generation of standard PDF 1.4 document.
        Produces compliant PDF without external C-extensions.
        """
        stream_lines = []
        # Title and header
        stream_lines.append("BT")
        stream_lines.append("/F1 14 Tf")
        stream_lines.append("50 750 Td")
        safe_title = title.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_lines.append(f"({safe_title}) Tj")
        stream_lines.append("ET")

        stream_lines.append("BT")
        stream_lines.append("/F1 9 Tf")
        stream_lines.append("50 732 Td")
        safe_sub = subtitle.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_lines.append(f"({safe_sub}) Tj")
        stream_lines.append("ET")

        # Table Header
        header_text = " | ".join(headers)
        stream_lines.append("BT")
        stream_lines.append("/F1 9 Tf")
        stream_lines.append("50 705 Td")
        safe_h = header_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_lines.append(f"({safe_h}) Tj")
        stream_lines.append("ET")

        # Separator line
        stream_lines.append("BT")
        stream_lines.append("/F1 8 Tf")
        stream_lines.append("50 695 Td")
        stream_lines.append(f"({'=' * min(80, len(header_text))}) Tj")
        stream_lines.append("ET")

        y = 680
        for row in rows[:35]:  # fit on page
            row_text = " | ".join(str(c) for c in row)
            safe_row = row_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_lines.append("BT")
            stream_lines.append("/F1 8 Tf")
            stream_lines.append(f"50 {y} Td")
            stream_lines.append(f"({safe_row}) Tj")
            stream_lines.append("ET")
            y -= 14

        stream_content = "\n".join(stream_lines).encode("latin1", errors="replace")
        stream_len = len(stream_content)

        objects = []
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>\nendobj\n")
        objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
        objects.append(f"5 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii") + stream_content + b"\nendstream\nendobj\n")

        header = b"%PDF-1.4\n"
        body = b""
        offsets = [0]
        curr_offset = len(header)

        for obj in objects:
            offsets.append(curr_offset)
            curr_offset += len(obj)
            body += obj

        xref_offset = curr_offset
        xref = f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii")
        for off in offsets[1:]:
            xref += f"{off:010d} 00000 n \n".encode("ascii")

        trailer = f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        return header + body + xref + trailer

    @staticmethod
    def export_assessment_report_pdf(
        db: Session,
        assessment_id: str,
        current_user: User
    ) -> Response:
        """
        Exports authorized, complete assessment performance report in PDF format.
        Strictly enforces tenant boundary and role authorization.
        """
        from app.dependencies import verify_tenant_access
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Enforce RBAC & Tenant Isolation
        if current_user.role == Role.CANDIDATE:
            raise HTTPException(status_code=403, detail="Candidates are forbidden from exporting assessment reports")
        verify_tenant_access(assessment.org_id, current_user, db)

        # Audit export action
        AuditService.log_event(
            db,
            event_type="ASSESSMENT_REPORT_EXPORTED",
            user_id=current_user.id,
            email=current_user.email,
            org_id=assessment.org_id,
            details={"assessment_id": assessment_id, "format": "PDF"}
        )

        attempts = db.query(Attempt).filter(
            Attempt.assessment_id == assessment_id,
            Attempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED])
        ).order_by(Attempt.rank.asc().nullslast()).all()

        headers = ["Rank", "Candidate", "Score", "Max", "Pct", "Result", "Percentile", "Risk"]
        rows = []
        for att in attempts:
            rows.append([
                str(att.rank or "N/A"),
                f"{att.candidate_name}",
                f"{att.total_score:.2f}",
                f"{att.total_max_marks:.2f}",
                f"{att.percentage:.1f}%",
                "PASS" if att.is_passed else "FAIL",
                f"{att.percentile:.1f}%" if att.percentile is not None else "N/A",
                att.risk_level.value if att.risk_level else "LOW"
            ])

        pdf_bytes = EvaluationService.generate_pdf_document(
            title=f"ProctorAI Assessment Report: {assessment.title}",
            subtitle=f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Passing: {assessment.passing_percentage}%",
            headers=headers,
            rows=rows
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=assessment_{assessment_id}_report.pdf"
            }
        )

    @staticmethod
    def export_assessment_report_csv(
        db: Session,
        assessment_id: str,
        current_user: User
    ) -> Response:
        """
        Exports authorized, complete assessment performance report in CSV format.
        Strictly enforces tenant boundary and role authorization.
        """
        from app.dependencies import verify_tenant_access
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Enforce RBAC & Tenant Isolation
        if current_user.role == Role.CANDIDATE:
            raise HTTPException(status_code=403, detail="Candidates are forbidden from exporting assessment reports")
        verify_tenant_access(assessment.org_id, current_user, db)

        # Audit export action
        AuditService.log_event(
            db,
            event_type="ASSESSMENT_REPORT_EXPORTED",
            user_id=current_user.id,
            email=current_user.email,
            org_id=assessment.org_id,
            details={"assessment_id": assessment_id, "format": "CSV"}
        )

        attempts = db.query(Attempt).filter(
            Attempt.assessment_id == assessment_id,
            Attempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED])
        ).order_by(Attempt.rank.asc().nullslast()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Rank",
            "Candidate Name",
            "Candidate Email",
            "Status",
            "Submission Receipt",
            "Submission Type",
            "Total Score",
            "Max Marks",
            "Percentage",
            "Result",
            "Percentile",
            "Risk Score",
            "Submitted At"
        ])

        for att in attempts:
            writer.writerow([
                att.rank or "N/A",
                att.candidate_name,
                att.candidate_email,
                att.status.value,
                att.submission_receipt or "N/A",
                att.submission_type or "MANUAL",
                att.total_score,
                att.total_max_marks,
                f"{att.percentage}%",
                "PASSED" if att.is_passed else "FAILED",
                f"{att.percentile}%" if att.percentile is not None else "N/A",
                att.risk_score,
                att.submitted_at.isoformat() if att.submitted_at else "N/A"
            ])

        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=assessment_{assessment_id}_report.csv"
            }
        )
