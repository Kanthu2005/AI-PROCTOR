from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Role
from app.models.attempt import Attempt, AttemptStatus
from app.schemas.attempt import (
    AutoSaveRequest, AutoSaveResponse, SubmitAttemptRequest, AttemptResultResponse
)
from app.services.attempt_service import AttemptService
from app.services.analytics_service import AnalyticsService
from app.services.evaluation_service import EvaluationService
from app.schemas.evaluation import (
    ManualEvaluationRequest, ManualEvaluationResponse, AISuggestScoreResponse, EvaluationResultResponse
)
from app.dependencies import get_current_user, require_roles, verify_tenant_access

router = APIRouter(prefix="/attempts", tags=["Candidate Test Engine & Attempts"])


@router.post("/start", response_model=Dict[str, Any])
def start_attempt(
    invitation_token: str,
    request: Request,
    seb_request_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-RequestHash"),
    seb_config_key_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-ConfigKeyHash"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    db: Session = Depends(get_db)
):
    """
    Candidate launches assessment:
    - Authoritative server-side timer starts (`server_expiry_at = server_time + duration`)
    - Validates Safe Exam Browser client hashes if assessment requires high-security mode
    - Returns sanitized exam questions (stripped of cheat keys)
    - Sets candidate status to STARTED -> IN_PROGRESS
    """
    return AttemptService.start_attempt(
        db,
        invitation_token,
        request_url=str(request.url),
        seb_request_hash=seb_request_hash,
        seb_config_key_hash=seb_config_key_hash,
        user_agent=user_agent
    )


@router.post("/{attempt_id}/answers/autosave", response_model=AutoSaveResponse)
def autosave_answers(
    attempt_id: str,
    save_in: AutoSaveRequest,
    request: Request,
    seb_request_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-RequestHash"),
    seb_config_key_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-ConfigKeyHash"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    db: Session = Depends(get_db)
):
    """
    Secure background auto-save endpoint.
    If server_time > server_expiry_at, automatically executes auto-submit and locks answers.
    Persists answer choices, code responses, review flags, and current active question.
    """
    return AttemptService.autosave_answers(
        db,
        attempt_id,
        save_in.answers,
        current_question_id=save_in.current_question_id,
        request_url=str(request.url),
        seb_request_hash=seb_request_hash,
        seb_config_key_hash=seb_config_key_hash,
        user_agent=user_agent
    )


@router.get("/{attempt_id}/state", response_model=Dict[str, Any])
def get_attempt_state(
    attempt_id: str,
    request: Request,
    seb_request_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-RequestHash"),
    seb_config_key_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-ConfigKeyHash"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    db: Session = Depends(get_db)
):
    """
    Reconnect & browser-refresh recovery endpoint:
    Returns current attempt state, authoritative timer, saved answers, and question palette status.
    """
    return AttemptService.get_attempt_state(
        db,
        attempt_id,
        request_url=str(request.url),
        seb_request_hash=seb_request_hash,
        seb_config_key_hash=seb_config_key_hash,
        user_agent=user_agent
    )


@router.post("/{attempt_id}/submit", response_model=Dict[str, Any])
def submit_attempt(
    attempt_id: str,
    request: Request,
    submit_in: SubmitAttemptRequest = SubmitAttemptRequest(),
    seb_request_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-RequestHash"),
    seb_config_key_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-ConfigKeyHash"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    db: Session = Depends(get_db)
):
    """
    Manual or auto submission of candidate attempt:
    - Triggers automated evaluation of MCQs (with negative marking) and Coding test cases
    - Generates tamper-proof submission receipt
    - Updates rankings and percentiles across the cohort
    - Returns comprehensive submission receipt and status
    """
    attempt = AttemptService.submit_attempt(
        db,
        attempt_id,
        final_answers=submit_in.final_answers,
        is_auto_submit=False,
        request_url=str(request.url),
        seb_request_hash=seb_request_hash,
        seb_config_key_hash=seb_config_key_hash,
        user_agent=user_agent
    )
    # Recompute cohort rankings
    AnalyticsService.compute_rankings_and_percentiles(db, attempt.assessment_id)
    db.refresh(attempt)

    # Compute question counts for submission receipt
    from app.models.assessment import SectionQuestion
    total_q = db.query(SectionQuestion).join(SectionQuestion.section).filter(
        SectionQuestion.section.has(assessment_id=attempt.assessment_id)
    ).count()

    answered_count = len([
        a for a in attempt.answers
        if (a.selected_option_ids and len(a.selected_option_ids) > 0)
        or (a.text_response and len(a.text_response.strip()) > 0)
        or (a.code_response and len(a.code_response.strip()) > 0)
    ])
    flagged_count = len([a for a in attempt.answers if a.is_flagged_for_review])
    unanswered_count = max(0, total_q - answered_count)

    return {
        "attempt_id": attempt.id,
        "candidate_name": attempt.candidate_name,
        "candidate_email": attempt.candidate_email,
        "status": attempt.status.value,
        "submission_receipt": attempt.submission_receipt,
        "submission_type": attempt.submission_type or "MANUAL",
        "total_score": attempt.total_score,
        "total_max_marks": attempt.total_max_marks,
        "percentage": attempt.percentage,
        "is_passed": attempt.is_passed,
        "rank": attempt.rank,
        "percentile": attempt.percentile,
        "risk_score": attempt.risk_score,
        "risk_level": attempt.risk_level.value,
        "submitted_at": attempt.submitted_at,
        "total_questions": total_q,
        "answered_count": answered_count,
        "unanswered_count": unanswered_count,
        "flagged_count": flagged_count
    }


@router.get("/{attempt_id}/result", response_model=Dict[str, Any])
def get_attempt_result(
    attempt_id: str,
    db: Session = Depends(get_db)
):
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    section_breakdown = []
    answers = attempt.answers
    for ans in answers:
        section_breakdown.append({
            "question_id": ans.question_id,
            "section_id": ans.section_id,
            "marks_awarded": ans.marks_awarded,
            "is_correct": ans.is_correct,
            "time_spent_seconds": ans.time_spent_seconds,
            "is_flagged_for_review": ans.is_flagged_for_review
        })

    return {
        "attempt_id": attempt.id,
        "assessment_id": attempt.assessment_id,
        "candidate_name": attempt.candidate_name,
        "candidate_email": attempt.candidate_email,
        "status": attempt.status.value,
        "submission_receipt": attempt.submission_receipt,
        "submission_type": attempt.submission_type or "MANUAL",
        "total_score": attempt.total_score,
        "total_max_marks": attempt.total_max_marks,
        "percentage": attempt.percentage,
        "is_passed": attempt.is_passed,
        "rank": attempt.rank,
        "percentile": attempt.percentile,
        "risk_score": attempt.risk_score,
        "risk_level": attempt.risk_level.value,
        "human_review_status": attempt.human_review_status.value,
        "evaluation_status": getattr(attempt, 'evaluation_status', 'FULLY_EVALUATED'),
        "section_scores": attempt.section_scores or {},
        "submitted_at": attempt.submitted_at,
        "section_breakdown": section_breakdown
    }


@router.post("/{attempt_id}/evaluate", response_model=EvaluationResultResponse)
def evaluate_attempt(
    attempt_id: str,
    recompute_all: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Authoritative server-side evaluation:
    - Re-evaluates attempt answers deterministically
    - Calculates section scores, totals, percentages, and pass/fail rules
    - Recomputes cohort rankings
    - Strict role enforcement
    """
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    verify_tenant_access(attempt.assessment.org_id, current_user, db)

    eval_attempt = EvaluationService.evaluate_attempt(db, attempt_id, recompute_all=recompute_all)
    AnalyticsService.compute_rankings_and_percentiles(db, eval_attempt.assessment_id)
    db.refresh(eval_attempt)

    return EvaluationResultResponse(
        attempt_id=eval_attempt.id,
        assessment_id=eval_attempt.assessment_id,
        candidate_name=eval_attempt.candidate_name,
        candidate_email=eval_attempt.candidate_email,
        status=eval_attempt.status.value,
        evaluation_status=eval_attempt.evaluation_status or "FULLY_EVALUATED",
        total_score=eval_attempt.total_score,
        total_max_marks=eval_attempt.total_max_marks,
        percentage=eval_attempt.percentage,
        is_passed=eval_attempt.is_passed,
        rank=eval_attempt.rank,
        percentile=eval_attempt.percentile,
        section_scores=eval_attempt.section_scores or {},
        submitted_at=eval_attempt.submitted_at
    )


@router.post("/{attempt_id}/answers/{question_id}/evaluate", response_model=ManualEvaluationResponse)
def manual_evaluate_answer(
    attempt_id: str,
    question_id: str,
    eval_req: ManualEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Manual evaluation of descriptive/short answer question by reviewer:
    - Validates marks bounded by question positive marks
    - Logs audit trail with old and new score
    - Recalculates attempt totals, section cutoffs, pass/fail rules, and cohort rankings
    """
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    verify_tenant_access(attempt.assessment.org_id, current_user, db)

    answer = EvaluationService.manual_evaluate_answer(
        db,
        attempt_id=attempt_id,
        question_id=question_id,
        marks_awarded=eval_req.marks_awarded,
        reviewer_comments=eval_req.reviewer_comments,
        reviewer=current_user
    )

    return ManualEvaluationResponse(
        attempt_id=answer.attempt_id,
        question_id=answer.question_id,
        marks_awarded=answer.marks_awarded,
        is_correct=answer.is_correct,
        reviewer_comments=answer.reviewer_comments,
        is_manually_evaluated=answer.is_manually_evaluated,
        evaluated_at=answer.evaluated_at,
        evaluated_by_id=answer.evaluated_by_id
    )


@router.post("/{attempt_id}/answers/{question_id}/suggest-score", response_model=AISuggestScoreResponse)
def suggest_descriptive_score(
    attempt_id: str,
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    AI-suggested score generation for descriptive responses:
    - Provides suggestion, confidence, and rationale
    - Strictly requires human confirmation before committing official marks
    """
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    verify_tenant_access(attempt.assessment.org_id, current_user, db)

    suggestion = EvaluationService.suggest_descriptive_score(
        db,
        attempt_id=attempt_id,
        question_id=question_id
    )
    return AISuggestScoreResponse(**suggestion)
