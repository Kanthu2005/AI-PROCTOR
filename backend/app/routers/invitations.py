from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User, Role
from app.models.invitation import ExamInvitation
from app.schemas.invitation import (
    SendExamInvitationsRequest,
    SendExamInvitationsResponse,
    ExamInvitationPreviewRequest,
    ExamInvitationPreviewResponse,
    ExamInvitationItemResponse,
    InvitationValidateResponse,
    EmailWebhookRequest
)
from app.services.email_service import EmailService

router = APIRouter(tags=["Exam Invitations & Real Email Delivery"])

AUTHORIZED_RECRUITER_ROLES = [Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN]


@router.post(
    "/assessments/{assessment_id}/invitations",
    response_model=SendExamInvitationsResponse,
    status_code=status.HTTP_201_CREATED
)
def send_exam_invitations(
    assessment_id: str,
    payload: SendExamInvitationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_RECRUITER_ROLES))
):
    """
    Sends real email invitations directly to selected candidates' email addresses.
    Creates audit records, validates recipients, logs provider message IDs, and handles retries.
    """
    candidates_dict = [c.model_dump() for c in payload.candidates]
    results = EmailService.send_assessment_invitations(
        db=db,
        assessment_id=assessment_id,
        recipients=candidates_dict,
        current_user=current_user,
        expires_in_hours=payload.expires_in_hours
    )

    total_sent = sum(1 for r in results if r["status"] in ("SENT", "DELIVERED"))
    total_failed = sum(1 for r in results if r["status"] == "FAILED")

    return SendExamInvitationsResponse(
        total_processed=len(results),
        total_sent=total_sent,
        total_failed=total_failed,
        invitations=results
    )


@router.post(
    "/assessments/{assessment_id}/invitations/preview",
    response_model=ExamInvitationPreviewResponse
)
def preview_invitation_email(
    assessment_id: str,
    payload: Optional[ExamInvitationPreviewRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_RECRUITER_ROLES))
):
    """
    Previews the responsive HTML and plain-text invitation email before triggering real delivery.
    """
    sample_name = payload.sample_name if payload else None
    sample_email = payload.sample_email if payload else None

    preview_data = EmailService.preview_invitation(
        db=db,
        assessment_id=assessment_id,
        sample_name=sample_name,
        sample_email=sample_email,
        current_user=current_user
    )
    return ExamInvitationPreviewResponse(**preview_data)


@router.get(
    "/assessments/{assessment_id}/invitations",
    response_model=List[ExamInvitationItemResponse]
)
def list_assessment_invitations(
    assessment_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_RECRUITER_ROLES, Role.PROCTOR))
):
    """
    Lists sent invitation history, delivery status, provider message IDs, and retry attempts
    for authorized recruiters.
    """
    invitations = EmailService.list_assessment_invitations(
        db=db,
        assessment_id=assessment_id,
        current_user=current_user,
        status_filter=status
    )
    return invitations


@router.post(
    "/invitations/{invitation_id}/resend",
    response_model=Dict[str, Any]
)
def resend_invitation(
    invitation_id: str,
    expires_in_hours: int = 72,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_RECRUITER_ROLES))
):
    """
    Resends an invitation to the candidate with a freshly refreshed cryptographic token.
    """
    return EmailService.resend_invitation(
        db=db,
        invitation_id=invitation_id,
        current_user=current_user,
        expires_in_hours=expires_in_hours
    )


@router.post(
    "/invitations/{invitation_id}/remind",
    response_model=Dict[str, Any]
)
def send_reminder(
    invitation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_RECRUITER_ROLES))
):
    """
    Sends an assessment reminder email to candidates with active invitations.
    """
    return EmailService.send_reminder(
        db=db,
        invitation_id=invitation_id,
        current_user=current_user
    )


@router.get(
    "/invitations/validate/{token}",
    response_model=InvitationValidateResponse
)
def validate_invitation(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Public validation endpoint called when candidate opens the secure invitation email link.
    Validates token, enforces scheduling windows and attempt restrictions without exposing answers.
    """
    return EmailService.validate_invitation_token(db, token)


@router.get(
    "/candidate/invitations",
    response_model=List[Dict[str, Any]]
)
def list_candidate_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists exam invitations assigned to the authenticated candidate.
    """
    query = db.query(ExamInvitation).filter(
        ExamInvitation.recipient_email == current_user.email.lower()
    ).order_by(ExamInvitation.created_at.desc())

    invitations = query.all()
    results = []
    for inv in invitations:
        cand_inv = inv.candidate_invitation
        attempt = cand_inv.attempt if cand_inv else None
        assessment = inv.assessment

        results.append({
            "id": inv.id,
            "assessment_id": inv.assessment_id,
            "assessment_title": assessment.title if assessment else "Assessment",
            "assessment_description": assessment.description if assessment else "",
            "duration_minutes": assessment.total_duration_minutes if assessment else 60,
            "total_marks": assessment.total_marks if assessment else 100.0,
            "recipient_email": inv.recipient_email,
            "recipient_name": inv.recipient_name,
            "status": inv.status.value,
            "sent_at": inv.sent_at.isoformat() if inv.sent_at else None,
            "delivered_at": inv.delivered_at.isoformat() if inv.delivered_at else None,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "invitation_token": cand_inv.invitation_token if cand_inv else "",
            "attempt_id": attempt.id if attempt else None,
            "attempt_status": attempt.status.value if attempt else None,
            "total_score": attempt.total_score if attempt else None,
            "is_passed": attempt.is_passed if attempt else None
        })
    return results


@router.post(
    "/invitations/webhook",
    status_code=status.HTTP_200_OK
)
async def provider_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook receiver for email provider event updates (e.g. Resend / SendGrid / SES).
    Confirms 'delivered', 'opened', 'bounced' states.
    """
    body = await request.json()
    event_type = body.get("type") or body.get("event") or "delivered"
    data = body.get("data") or body
    
    # Resend format: {"type": "email.delivered", "data": {"email_id": "...", ...}}
    provider_msg_id = (
        data.get("email_id")
        or data.get("id")
        or data.get("message_id")
        or body.get("email_id")
    )
    error_msg = data.get("error") or data.get("reason")

    if provider_msg_id:
        EmailService.handle_webhook(
            db=db,
            event_type=event_type,
            provider_message_id=str(provider_msg_id),
            error_message=str(error_msg) if error_msg else None
        )

    return {"status": "received", "event": event_type}
