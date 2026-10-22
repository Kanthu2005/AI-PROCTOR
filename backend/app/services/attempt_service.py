import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus, RiskLevel, HumanReviewStatus
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.assessment import Assessment, AssessmentStatus, SectionQuestion
from app.models.question import QuestionVersion, QuestionType
from app.schemas.attempt import AutoSaveItem, AutoSaveResponse, AttemptStartResponse, AttemptResultResponse
from app.services.assessment_service import AssessmentService
from app.services.sandbox_service import CodingSandboxRunner
from app.utils.security import is_demo_replayable_token


def generate_submission_receipt(attempt_id: str, candidate_email: str, submitted_at: datetime) -> str:
    raw = f"{attempt_id}:{candidate_email}:{submitted_at.isoformat()}:{uuid.uuid4().hex}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
    return f"RCPT-{attempt_id[:6].upper()}-{digest}"


class AttemptService:
    @staticmethod
    def start_attempt(
        db: Session,
        invitation_token: str,
        request_url: Optional[str] = None,
        seb_request_hash: Optional[str] = None,
        seb_config_key_hash: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Starts or resumes a candidate attempt with server-side authoritative timer.
        Recovers saved answers, review flags, and deterministic question ordering.
        Enforces Safe Exam Browser cryptographic verification when seb_required is set.
        """
        invitation = db.query(CandidateInvitation).filter(
            CandidateInvitation.invitation_token == invitation_token
        ).first()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if invitation.status == CandidateStatus.DISQUALIFIED:
            raise HTTPException(status_code=403, detail="Candidate is disqualified from this assessment")

        now_utc = datetime.now(timezone.utc)
        expires_at_utc = invitation.expires_at.replace(tzinfo=timezone.utc) if invitation.expires_at.tzinfo is None else invitation.expires_at
        if now_utc > expires_at_utc:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation link has expired")

        if invitation.status == CandidateStatus.SUBMITTED:
            if is_demo_replayable_token(invitation.invitation_token):
                invitation.status = CandidateStatus.REGISTERED
                invitation.system_check_passed = True
                db.commit()
            else:
                raise HTTPException(status_code=400, detail="Assessment has already been submitted")

        if not invitation.system_check_passed:
            if is_demo_replayable_token(invitation.invitation_token):
                invitation.system_check_passed = True
                db.commit()
            else:
                raise HTTPException(
                    status_code=400,
                    detail="System compatibility check must be completed before starting"
                )

        assessment = invitation.assessment
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Validate assessment lifecycle state
        if assessment.status == AssessmentStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot take assessment in 'CLOSED' status"
            )



        # Validate schedule window if applicable
        if assessment.start_time and assessment.status == AssessmentStatus.SCHEDULED:
            start_utc = assessment.start_time.replace(tzinfo=timezone.utc) if assessment.start_time.tzinfo is None else assessment.start_time
            if now_utc < start_utc:
                raise HTTPException(status_code=400, detail="Assessment scheduled window has not started yet")
        if assessment.end_time:
            end_utc = assessment.end_time.replace(tzinfo=timezone.utc) if assessment.end_time.tzinfo is None else assessment.end_time
            if now_utc > end_utc:
                raise HTTPException(status_code=400, detail="Assessment scheduled window has ended")

        # Safe Exam Browser (SEB) High-Security Mode Verification
        seb_res = None
        if assessment.rules and assessment.rules.seb_required:
            from app.services.seb_service import SafeExamBrowserService
            seb_res = SafeExamBrowserService.verify_seb_request(
                assessment=assessment,
                request_url=request_url or "",
                request_hash=seb_request_hash,
                config_key_hash=seb_config_key_hash,
                user_agent=user_agent
            )
            if not seb_res.is_valid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": seb_res.error_code or "SEB_CLIENT_REQUIRED",
                        "message": seb_res.detail,
                        "lockdown_guaranteed": False,
                        "platform_detected": seb_res.platform
                    }
                )

        # Check if attempt already exists
        attempt = db.query(Attempt).filter(Attempt.invitation_id == invitation.id).first()

        # If previous attempt is already submitted or expired on a demo token, reset it (dev only)
        if attempt and (attempt.status == AttemptStatus.SUBMITTED or (attempt.server_expiry_at and now_utc > (attempt.server_expiry_at.replace(tzinfo=timezone.utc) if attempt.server_expiry_at.tzinfo is None else attempt.server_expiry_at))):
            if is_demo_replayable_token(invitation.invitation_token):
                db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).delete()
                db.delete(attempt)
                db.commit()
                attempt = None

        if not attempt:
            # Server-controlled authoritative deadline:
            # Clamped by assessment.end_time if configured
            duration_deadline = now_utc + timedelta(minutes=assessment.total_duration_minutes)
            if assessment.end_time:
                end_utc = assessment.end_time.replace(tzinfo=timezone.utc) if assessment.end_time.tzinfo is None else assessment.end_time
                server_expiry_at = min(duration_deadline, end_utc)
            else:
                server_expiry_at = duration_deadline

            attempt = Attempt(
                invitation_id=invitation.id,
                assessment_id=assessment.id,
                candidate_email=invitation.email,
                candidate_name=invitation.full_name,
                status=AttemptStatus.IN_PROGRESS,
                started_at=now_utc,
                server_expiry_at=server_expiry_at,
                last_activity_at=now_utc,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                human_review_status=HumanReviewStatus.PENDING,
                tab_switch_count=0,
                seb_verified=True if (assessment.rules and assessment.rules.seb_required) else False,
                seb_verification_mechanism=seb_res.mechanism if seb_res else None,
                seb_verified_at=now_utc if (assessment.rules and assessment.rules.seb_required) else None,
                seb_client_platform=seb_res.platform if seb_res else None,
                seb_client_user_agent=user_agent[:255] if user_agent else None
            )
            db.add(attempt)
            invitation.status = CandidateStatus.IN_PROGRESS
            db.commit()
            db.refresh(attempt)
        else:
            # Reconnect & recovery check: verify SEB mode
            if assessment.rules and assessment.rules.seb_required:
                if not attempt.seb_verified:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": "SEB_CLIENT_REQUIRED",
                            "message": "Attempt was not started in verified Safe Exam Browser session.",
                            "lockdown_guaranteed": False
                        }
                    )
            expiry_utc = attempt.server_expiry_at.replace(tzinfo=timezone.utc) if attempt.server_expiry_at.tzinfo is None else attempt.server_expiry_at
            if now_utc > expiry_utc and attempt.status == AttemptStatus.IN_PROGRESS:
                AttemptService.submit_attempt(db, attempt.id, is_auto_submit=True)
                raise HTTPException(status_code=400, detail="Assessment timer has expired and test has been auto-submitted")
            attempt.last_activity_at = now_utc
            db.commit()

        # Compute remaining seconds strictly from authoritative server timer
        expiry_utc = attempt.server_expiry_at.replace(tzinfo=timezone.utc) if attempt.server_expiry_at.tzinfo is None else attempt.server_expiry_at
        remaining_seconds = max(0, int((expiry_utc - now_utc).total_seconds()))

        # Deterministic question ordering and options using attempt.id as seed
        candidate_view = AssessmentService.get_candidate_assessment_view(
            db, assessment.id, candidate_seed=attempt.id
        )

        # Collect all previously saved answers for seamless browser-refresh recovery
        saved_answers_map = {}
        answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
        for ans in answers:
            saved_answers_map[ans.question_id] = {
                "question_id": ans.question_id,
                "question_version_id": ans.question_version_id,
                "section_id": ans.section_id,
                "selected_option_ids": ans.selected_option_ids or [],
                "text_response": ans.text_response or "",
                "code_response": ans.code_response or "",
                "language": ans.language or "",
                "time_spent_seconds": ans.time_spent_seconds or 0,
                "is_flagged_for_review": ans.is_flagged_for_review or False
            }

        return {
            "attempt_id": attempt.id,
            "assessment_id": assessment.id,
            "assessment_title": assessment.title,
            "candidate_name": attempt.candidate_name,
            "candidate_email": attempt.candidate_email,
            "status": attempt.status.value,
            "started_at": attempt.started_at,
            "server_time": now_utc,
            "server_expiry_at": attempt.server_expiry_at,
            "remaining_seconds": remaining_seconds,
            "total_marks": assessment.total_marks,
            "passing_percentage": assessment.passing_percentage,
            "current_question_id": attempt.current_question_id,
            "submission_receipt": attempt.submission_receipt,
            "saved_answers": saved_answers_map,
            "rules": candidate_view["rules"],
            "sections": candidate_view["sections"]
        }

    @staticmethod
    def autosave_answers(
        db: Session,
        attempt_id: str,
        answers: List[AutoSaveItem],
        current_question_id: Optional[str] = None,
        request_url: Optional[str] = None,
        seb_request_hash: Optional[str] = None,
        seb_config_key_hash: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AutoSaveResponse:
        """
        Background autosave endpoint with authoritative server timer check.
        If server_time > server_expiry_at, securely triggers auto-submit.
        Handles retry-safe upserts and mark-for-review state preservation.
        Enforces Safe Exam Browser lockdown evidence if seb_required.
        """
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        # SEB verification check
        assessment = attempt.assessment
        if assessment and assessment.rules and assessment.rules.seb_required:
            if not attempt.seb_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "SEB_CLIENT_REQUIRED",
                        "message": "Attempt was not started in verified Safe Exam Browser session.",
                        "lockdown_guaranteed": False
                    }
                )
            if request_url and (seb_request_hash or seb_config_key_hash):
                from app.services.seb_service import SafeExamBrowserService
                seb_res = SafeExamBrowserService.verify_seb_request(
                    assessment=assessment,
                    request_url=request_url,
                    request_hash=seb_request_hash,
                    config_key_hash=seb_config_key_hash,
                    user_agent=user_agent
                )
                if not seb_res.is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": seb_res.error_code or "SEB_HASH_MISMATCH",
                            "message": seb_res.detail,
                            "lockdown_guaranteed": False
                        }
                    )

        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot save answers: attempt is currently in '{attempt.status.value}' status"
            )

        now_utc = datetime.now(timezone.utc)
        expiry_utc = attempt.server_expiry_at.replace(tzinfo=timezone.utc) if attempt.server_expiry_at.tzinfo is None else attempt.server_expiry_at

        # Authoritative Server Timer Expiration Auto-Submit:
        if now_utc > expiry_utc:
            submitted_attempt = AttemptService.submit_attempt(db, attempt_id, final_answers=answers, is_auto_submit=True)
            return AutoSaveResponse(
                success=True,
                saved_count=len(answers),
                server_time=now_utc,
                server_expiry_at=attempt.server_expiry_at,
                remaining_seconds=0,
                is_auto_submitted=True,
                saved_question_ids=[a.question_id for a in answers],
                submission_receipt=submitted_attempt.submission_receipt
            )

        # Save or update each answer retry-safely
        saved_count = 0
        saved_q_ids = []
        for item in answers:
            ans = db.query(AttemptAnswer).filter(
                AttemptAnswer.attempt_id == attempt_id,
                AttemptAnswer.question_id == item.question_id
            ).first()

            if not ans:
                ans = AttemptAnswer(
                    attempt_id=attempt_id,
                    question_id=item.question_id,
                    question_version_id=item.question_version_id,
                    section_id=item.section_id,
                    selected_option_ids=item.selected_option_ids,
                    text_response=item.text_response,
                    code_response=item.code_response,
                    language=item.language,
                    time_spent_seconds=item.time_spent_seconds,
                    is_flagged_for_review=item.is_flagged_for_review
                )
                db.add(ans)
            else:
                ans.selected_option_ids = item.selected_option_ids
                ans.text_response = item.text_response
                ans.code_response = item.code_response
                ans.language = item.language
                ans.time_spent_seconds = item.time_spent_seconds
                ans.is_flagged_for_review = item.is_flagged_for_review

            saved_count += 1
            saved_q_ids.append(item.question_id)

        attempt.last_activity_at = now_utc
        if current_question_id:
            attempt.current_question_id = current_question_id

        db.commit()
        remaining_seconds = max(0, int((expiry_utc - now_utc).total_seconds()))

        return AutoSaveResponse(
            success=True,
            saved_count=saved_count,
            server_time=now_utc,
            server_expiry_at=attempt.server_expiry_at,
            remaining_seconds=remaining_seconds,
            is_auto_submitted=False,
            saved_question_ids=saved_q_ids,
            submission_receipt=attempt.submission_receipt
        )

    @staticmethod
    def submit_attempt(
        db: Session,
        attempt_id: str,
        final_answers: Optional[List[AutoSaveItem]] = None,
        is_auto_submit: bool = False,
        request_url: Optional[str] = None,
        seb_request_hash: Optional[str] = None,
        seb_config_key_hash: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Attempt:
        """
        Submits and evaluates candidate attempt:
        - Evaluates MCQ, True/False, Fill in Blank, and Coding questions
        - Generates tamper-proof submission receipt
        - Updates attempt status to SUBMITTED or AUTO_SUBMITTED
        - Updates candidate invitation status to SUBMITTED
        - Retry-safe and idempotent
        - Enforces Safe Exam Browser lockdown verification when seb_required is set
        """
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        # SEB verification check (unless auto-submit by server deadline)
        assessment = attempt.assessment
        if not is_auto_submit and assessment and assessment.rules and assessment.rules.seb_required:
            if not attempt.seb_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "SEB_CLIENT_REQUIRED",
                        "message": "Cannot submit: attempt was not verified in Safe Exam Browser.",
                        "lockdown_guaranteed": False
                    }
                )
            if request_url and (seb_request_hash or seb_config_key_hash):
                from app.services.seb_service import SafeExamBrowserService
                seb_res = SafeExamBrowserService.verify_seb_request(
                    assessment=assessment,
                    request_url=request_url,
                    request_hash=seb_request_hash,
                    config_key_hash=seb_config_key_hash,
                    user_agent=user_agent
                )
                if not seb_res.is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": seb_res.error_code or "SEB_HASH_MISMATCH",
                            "message": seb_res.detail,
                            "lockdown_guaranteed": False
                        }
                    )

        # Idempotent: return existing evaluated attempt if already submitted
        if attempt.status in [AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.DISQUALIFIED]:
            if not attempt.submission_receipt:
                now_utc = datetime.now(timezone.utc)
                attempt.submission_receipt = generate_submission_receipt(attempt.id, attempt.candidate_email, now_utc)
                db.commit()
            return attempt

        # If final answers passed, autosave them first
        if final_answers:
            for item in final_answers:
                ans = db.query(AttemptAnswer).filter(
                    AttemptAnswer.attempt_id == attempt_id,
                    AttemptAnswer.question_id == item.question_id
                ).first()
                if not ans:
                    ans = AttemptAnswer(
                        attempt_id=attempt_id,
                        question_id=item.question_id,
                        question_version_id=item.question_version_id,
                        section_id=item.section_id,
                        selected_option_ids=item.selected_option_ids,
                        text_response=item.text_response,
                        code_response=item.code_response,
                        language=item.language,
                        time_spent_seconds=item.time_spent_seconds,
                        is_flagged_for_review=item.is_flagged_for_review
                    )
                    db.add(ans)
                else:
                    ans.selected_option_ids = item.selected_option_ids
                    ans.text_response = item.text_response
                    ans.code_response = item.code_response
                    ans.language = item.language
                    ans.time_spent_seconds = item.time_spent_seconds
                    ans.is_flagged_for_review = item.is_flagged_for_review
            db.commit()

        # Delegate evaluation to authoritative EvaluationService
        from app.services.evaluation_service import EvaluationService
        attempt = EvaluationService.evaluate_attempt(db, attempt_id, recompute_all=True)

        now_utc = datetime.now(timezone.utc)
        attempt.submitted_at = now_utc
        attempt.status = AttemptStatus.AUTO_SUBMITTED if is_auto_submit else AttemptStatus.SUBMITTED
        attempt.submission_type = "AUTO_DEADLINE" if is_auto_submit else "MANUAL"
        if not attempt.submission_receipt:
            attempt.submission_receipt = generate_submission_receipt(attempt.id, attempt.candidate_email, now_utc)

        # Update candidate invitation status
        invitation = attempt.invitation
        if invitation:
            invitation.status = CandidateStatus.SUBMITTED

        db.commit()
        db.refresh(attempt)
        return attempt

    @staticmethod
    def get_attempt_state(
        db: Session,
        attempt_id: str,
        request_url: Optional[str] = None,
        seb_request_hash: Optional[str] = None,
        seb_config_key_hash: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reconnect & recovery state endpoint:
        Returns current attempt metadata, authoritative countdown, and saved answers.
        Enforces Safe Exam Browser lockdown verification when seb_required is set.
        """
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        # SEB verification check
        assessment = attempt.assessment
        if assessment and assessment.rules and assessment.rules.seb_required:
            if not attempt.seb_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "SEB_CLIENT_REQUIRED",
                        "message": "Cannot access attempt state: Safe Exam Browser is required.",
                        "lockdown_guaranteed": False
                    }
                )
            if request_url and (seb_request_hash or seb_config_key_hash):
                from app.services.seb_service import SafeExamBrowserService
                seb_res = SafeExamBrowserService.verify_seb_request(
                    assessment=assessment,
                    request_url=request_url,
                    request_hash=seb_request_hash,
                    config_key_hash=seb_config_key_hash,
                    user_agent=user_agent
                )
                if not seb_res.is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": seb_res.error_code or "SEB_HASH_MISMATCH",
                            "message": seb_res.detail,
                            "lockdown_guaranteed": False
                        }
                    )

        now_utc = datetime.now(timezone.utc)
        expiry_utc = attempt.server_expiry_at.replace(tzinfo=timezone.utc) if attempt.server_expiry_at and attempt.server_expiry_at.tzinfo is None else attempt.server_expiry_at
        remaining_seconds = 0
        if expiry_utc and attempt.status == AttemptStatus.IN_PROGRESS:
            remaining_seconds = max(0, int((expiry_utc - now_utc).total_seconds()))

        saved_answers_map = {}
        for ans in attempt.answers:
            saved_answers_map[ans.question_id] = {
                "question_id": ans.question_id,
                "question_version_id": ans.question_version_id,
                "section_id": ans.section_id,
                "selected_option_ids": ans.selected_option_ids or [],
                "text_response": ans.text_response or "",
                "code_response": ans.code_response or "",
                "language": ans.language or "",
                "time_spent_seconds": ans.time_spent_seconds or 0,
                "is_flagged_for_review": ans.is_flagged_for_review or False
            }

        candidate_view = AssessmentService.get_candidate_assessment_view(
            db, attempt.assessment_id, candidate_seed=attempt.id
        )

        return {
            "attempt_id": attempt.id,
            "assessment_id": attempt.assessment_id,
            "assessment_title": attempt.assessment.title if attempt.assessment else "Assessment",
            "candidate_name": attempt.candidate_name,
            "candidate_email": attempt.candidate_email,
            "status": attempt.status.value,
            "started_at": attempt.started_at,
            "server_time": now_utc,
            "server_expiry_at": attempt.server_expiry_at,
            "remaining_seconds": remaining_seconds,
            "submission_receipt": attempt.submission_receipt,
            "submission_type": attempt.submission_type,
            "current_question_id": attempt.current_question_id,
            "saved_answers": saved_answers_map,
            "rules": candidate_view["rules"],
            "sections": candidate_view["sections"]
        }
