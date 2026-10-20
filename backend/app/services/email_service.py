import hashlib
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple

from email_validator import validate_email, EmailNotValidError
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.assessment import Assessment
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.invitation import (
    ExamInvitation,
    ExamInvitationStatus,
    InvitationDeliveryAttempt,
    DeliveryAttemptType,
    DeliveryAttemptStatus,
)
from app.models.user import User, Role
from app.services.email.provider import get_email_provider, BaseEmailProvider
from app.services.email.templates import (
    render_exam_invitation_subject,
    render_exam_invitation_html,
    render_exam_invitation_text,
)
from app.utils.security import generate_invitation_token

logger = logging.getLogger("proctorai.email.service")


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of raw invitation token for secure storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class EmailService:
    @staticmethod
    def validate_recipient_email(raw_email: str) -> str:
        """Validates and normalizes candidate email address."""
        if not raw_email or not isinstance(raw_email, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email address is required."
            )
        try:
            valid = validate_email(raw_email.strip(), check_deliverability=False)
            return valid.normalized.lower()
        except EmailNotValidError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid recipient email address '{raw_email}': {str(exc)}"
            )

    @staticmethod
    def build_exam_link(raw_token: str) -> str:
        """Constructs secure public exam URL using configured frontend base URL."""
        base_url = settings.FRONTEND_BASE_URL.rstrip("/")
        return f"{base_url}/#/candidate_exam?token={raw_token}"

    @classmethod
    def preview_invitation(
        cls,
        db: Session,
        assessment_id: str,
        sample_name: Optional[str] = None,
        sample_email: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Generates preview of subject, HTML and plain-text body with real assessment metadata.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        candidate_name = sample_name or "Jane Candidate"
        candidate_email = sample_email or "candidate@example.com"
        mock_raw_token = "SECURE_SAMPLE_TOKEN_PREVIEW_ONLY"
        exam_link = cls.build_exam_link(mock_raw_token)

        start_str = (
            assessment.start_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.start_time else "Available immediately upon invitation"
        )
        end_str = (
            assessment.end_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.end_time else "Open window until deadline"
        )

        org_name = assessment.organization.name if assessment.organization else "ProctorAI Assessment Platform"
        recruiter_name = current_user.full_name if current_user else "Assessment Coordinator"
        recruiter_email = current_user.email if current_user else settings.EMAIL_FROM_ADDRESS

        context = {
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "assessment_title": assessment.title,
            "assessment_description": assessment.description or "Comprehensive Technical Evaluation",
            "duration": f"{assessment.total_duration_minutes} minutes",
            "start_datetime": start_str,
            "end_datetime": end_str,
            "total_marks": str(assessment.total_marks),
            "passing_marks": f"{int((assessment.passing_percentage / 100.0) * assessment.total_marks)} ({assessment.passing_percentage}%)",
            "exam_instructions": assessment.instructions or "Please ensure a quiet environment, functional webcam, and stable internet.",
            "secure_exam_link": exam_link,
            "recruiter_name": recruiter_name,
            "recruiter_email": recruiter_email,
            "organization_name": org_name,
        }

        subject = render_exam_invitation_subject(assessment.title)
        html_body = render_exam_invitation_html(context)
        text_body = render_exam_invitation_text(context)

        return {
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "context": context
        }

    @classmethod
    def send_assessment_invitations(
        cls,
        db: Session,
        assessment_id: str,
        recipients: List[Dict[str, str]],
        current_user: User,
        expires_in_hours: int = 72,
        provider_override: Optional[BaseEmailProvider] = None
    ) -> List[Dict[str, Any]]:
        """
        Sends real email invitations to selected candidates.
        Enforces tenant isolation, rate limits, token hashing, retry attempts, and status tracking.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Tenant isolation check
        if current_user.role != Role.PLATFORM_ADMIN and assessment.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to invite candidates to assessments belonging to another organization"
            )

        if not recipients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one candidate recipient is required"
            )

        if len(recipients) > settings.EMAIL_MAX_BULK_RECIPIENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceeded bulk recipient limit of {settings.EMAIL_MAX_BULK_RECIPIENTS} candidates per request"
            )

        provider = provider_override or get_email_provider()
        results = []
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(hours=expires_in_hours)

        start_str = (
            assessment.start_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.start_time else "Available immediately upon invitation"
        )
        end_str = (
            assessment.end_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.end_time else "Open window until deadline"
        )

        org_name = assessment.organization.name if assessment.organization else "ProctorAI Assessment Platform"
        recruiter_name = current_user.full_name or "Assessment Coordinator"
        recruiter_email = current_user.email or settings.EMAIL_FROM_ADDRESS

        for item in recipients:
            raw_email = item.get("email", "")
            raw_name = item.get("full_name") or item.get("name") or raw_email.split("@")[0].title()
            
            clean_email = cls.validate_recipient_email(raw_email)
            clean_name = raw_name.strip()

            # Check if matching user exists with CANDIDATE role
            candidate_user = db.query(User).filter(User.email == clean_email).first()
            candidate_user_id = candidate_user.id if candidate_user else None

            # Generate high-entropy cryptographic token
            raw_token = generate_invitation_token()
            token_hash = hash_token(raw_token)
            secure_exam_link = cls.build_exam_link(raw_token)

            # Sync with CandidateInvitation (preserving attempt and test engine compatibility)
            cand_inv = db.query(CandidateInvitation).filter(
                CandidateInvitation.assessment_id == assessment_id,
                CandidateInvitation.email == clean_email
            ).first()

            if cand_inv:
                cand_inv.invitation_token = raw_token
                cand_inv.expires_at = expires_at
                cand_inv.full_name = clean_name
                cand_inv.status = CandidateStatus.INVITED
            else:
                cand_inv = CandidateInvitation(
                    assessment_id=assessment_id,
                    org_id=assessment.org_id,
                    email=clean_email,
                    full_name=clean_name,
                    invitation_token=raw_token,
                    expires_at=expires_at,
                    status=CandidateStatus.INVITED,
                    system_check_passed=False
                )
                db.add(cand_inv)
            db.flush()

            # Create ExamInvitation record
            exam_inv = ExamInvitation(
                assessment_id=assessment_id,
                candidate_id=candidate_user_id,
                candidate_invitation_id=cand_inv.id,
                recipient_email=clean_email,
                recipient_name=clean_name,
                invitation_token_hash=token_hash,
                status=ExamInvitationStatus.PENDING,
                expires_at=expires_at,
                created_by=current_user.id
            )
            db.add(exam_inv)
            db.flush()

            # Render email
            context = {
                "candidate_name": clean_name,
                "candidate_email": clean_email,
                "assessment_title": assessment.title,
                "assessment_description": assessment.description or "Comprehensive Technical Evaluation",
                "duration": f"{assessment.total_duration_minutes} minutes",
                "start_datetime": start_str,
                "end_datetime": end_str,
                "total_marks": str(assessment.total_marks),
                "passing_marks": f"{int((assessment.passing_percentage / 100.0) * assessment.total_marks)} ({assessment.passing_percentage}%)",
                "exam_instructions": assessment.instructions or "Please follow all proctoring guidelines during the test.",
                "secure_exam_link": secure_exam_link,
                "recruiter_name": recruiter_name,
                "recruiter_email": recruiter_email,
                "organization_name": org_name,
            }

            subject = render_exam_invitation_subject(assessment.title)
            html_body = render_exam_invitation_html(context)
            text_body = render_exam_invitation_text(context)

            # Send email with retries for transient failures
            send_result = None
            max_retries = 2
            for attempt_num in range(max_retries + 1):
                send_result = provider.send_email(
                    to_email=clean_email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    from_email=settings.EMAIL_FROM_ADDRESS,
                    from_name=settings.EMAIL_FROM_NAME,
                    reply_to=recruiter_email
                )
                if send_result.success:
                    break
                if attempt_num < max_retries:
                    time.sleep(0.5 * (attempt_num + 1))  # exponential backoff

            # Record delivery attempt
            attempt_record = InvitationDeliveryAttempt(
                invitation_id=exam_inv.id,
                attempt_type=DeliveryAttemptType.INITIAL,
                provider=send_result.provider,
                status=DeliveryAttemptStatus.ACCEPTED if send_result.success else DeliveryAttemptStatus.FAILED,
                provider_message_id=send_result.message_id,
                error_message=send_result.error,
                duration_ms=send_result.duration_ms
            )
            db.add(attempt_record)

            if send_result.success:
                exam_inv.status = ExamInvitationStatus.SENT
                exam_inv.sent_at = datetime.now(timezone.utc)
                exam_inv.provider_message_id = send_result.message_id
                exam_inv.last_error = None
            else:
                exam_inv.status = ExamInvitationStatus.FAILED
                exam_inv.last_error = send_result.error

            db.commit()
            db.refresh(exam_inv)

            results.append({
                "invitation_id": exam_inv.id,
                "candidate_invitation_id": cand_inv.id,
                "recipient_email": clean_email,
                "recipient_name": clean_name,
                "status": exam_inv.status.value,
                "provider_message_id": exam_inv.provider_message_id,
                "sent_at": exam_inv.sent_at.isoformat() if exam_inv.sent_at else None,
                "expires_at": exam_inv.expires_at.isoformat() if exam_inv.expires_at else None,
                "error": exam_inv.last_error,
                "secure_exam_link": secure_exam_link
            })

        return results

    @classmethod
    def list_assessment_invitations(
        cls,
        db: Session,
        assessment_id: str,
        current_user: User,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists invitation records with delivery status and history for authorized recruiters."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        if current_user.role != Role.PLATFORM_ADMIN and assessment.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view invitations for another organization"
            )

        query = db.query(ExamInvitation).filter(ExamInvitation.assessment_id == assessment_id)
        if status_filter and status_filter.upper() != "ALL":
            query = query.filter(ExamInvitation.status == status_filter.upper())

        invitations = query.order_by(ExamInvitation.created_at.desc()).all()
        output = []
        for inv in invitations:
            attempts_summary = [
                {
                    "id": att.id,
                    "attempt_type": att.attempt_type.value,
                    "status": att.status.value,
                    "provider": att.provider,
                    "provider_message_id": att.provider_message_id,
                    "error_message": att.error_message,
                    "created_at": att.created_at.isoformat() if att.created_at else None
                }
                for att in inv.delivery_attempts
            ]

            output.append({
                "id": inv.id,
                "assessment_id": inv.assessment_id,
                "assessment_title": assessment.title,
                "candidate_id": inv.candidate_id,
                "recipient_email": inv.recipient_email,
                "recipient_name": inv.recipient_name,
                "status": inv.status.value,
                "sent_at": inv.sent_at.isoformat() if inv.sent_at else None,
                "delivered_at": inv.delivered_at.isoformat() if inv.delivered_at else None,
                "opened_at": inv.opened_at.isoformat() if inv.opened_at else None,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "provider_message_id": inv.provider_message_id,
                "last_error": inv.last_error,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "delivery_attempts_count": len(inv.delivery_attempts),
                "delivery_attempts": attempts_summary,
                "candidate_invitation_token": inv.candidate_invitation.invitation_token if inv.candidate_invitation else None
            })
        return output

    @classmethod
    def resend_invitation(
        cls,
        db: Session,
        invitation_id: str,
        current_user: User,
        expires_in_hours: int = 72,
        provider_override: Optional[BaseEmailProvider] = None
    ) -> Dict[str, Any]:
        """Resends an invitation with refreshed expiration and sends email directly."""
        inv = db.query(ExamInvitation).filter(ExamInvitation.id == invitation_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Exam invitation not found")

        assessment = inv.assessment
        if current_user.role != Role.PLATFORM_ADMIN and assessment.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to resend invitations for another organization"
            )

        # Generate fresh token
        new_raw_token = generate_invitation_token()
        new_token_hash = hash_token(new_raw_token)
        new_expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        secure_exam_link = cls.build_exam_link(new_raw_token)

        inv.invitation_token_hash = new_token_hash
        inv.expires_at = new_expires_at
        inv.status = ExamInvitationStatus.PENDING

        if inv.candidate_invitation:
            inv.candidate_invitation.invitation_token = new_raw_token
            inv.candidate_invitation.expires_at = new_expires_at
            inv.candidate_invitation.status = CandidateStatus.INVITED
            inv.candidate_invitation.system_check_passed = False

        db.flush()

        start_str = (
            assessment.start_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.start_time else "Available immediately upon invitation"
        )
        end_str = (
            assessment.end_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.end_time else "Open window until deadline"
        )

        org_name = assessment.organization.name if assessment.organization else "ProctorAI Assessment Platform"
        recruiter_name = current_user.full_name or "Assessment Coordinator"
        recruiter_email = current_user.email or settings.EMAIL_FROM_ADDRESS

        context = {
            "candidate_name": inv.recipient_name,
            "candidate_email": inv.recipient_email,
            "assessment_title": assessment.title,
            "assessment_description": assessment.description or "Comprehensive Technical Evaluation",
            "duration": f"{assessment.total_duration_minutes} minutes",
            "start_datetime": start_str,
            "end_datetime": end_str,
            "total_marks": str(assessment.total_marks),
            "passing_marks": f"{int((assessment.passing_percentage / 100.0) * assessment.total_marks)} ({assessment.passing_percentage}%)",
            "exam_instructions": assessment.instructions or "Please follow all proctoring guidelines during the test.",
            "secure_exam_link": secure_exam_link,
            "recruiter_name": recruiter_name,
            "recruiter_email": recruiter_email,
            "organization_name": org_name,
        }

        subject = render_exam_invitation_subject(assessment.title)
        html_body = render_exam_invitation_html(context)
        text_body = render_exam_invitation_text(context)

        provider = provider_override or get_email_provider()
        send_result = provider.send_email(
            to_email=inv.recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_email=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
            reply_to=recruiter_email
        )

        attempt = InvitationDeliveryAttempt(
            invitation_id=inv.id,
            attempt_type=DeliveryAttemptType.RESEND,
            provider=send_result.provider,
            status=DeliveryAttemptStatus.ACCEPTED if send_result.success else DeliveryAttemptStatus.FAILED,
            provider_message_id=send_result.message_id,
            error_message=send_result.error,
            duration_ms=send_result.duration_ms
        )
        db.add(attempt)

        if send_result.success:
            inv.status = ExamInvitationStatus.SENT
            inv.sent_at = datetime.now(timezone.utc)
            inv.provider_message_id = send_result.message_id
            inv.last_error = None
        else:
            inv.status = ExamInvitationStatus.FAILED
            inv.last_error = send_result.error

        db.commit()
        db.refresh(inv)

        return {
            "invitation_id": inv.id,
            "recipient_email": inv.recipient_email,
            "recipient_name": inv.recipient_name,
            "status": inv.status.value,
            "provider_message_id": inv.provider_message_id,
            "sent_at": inv.sent_at.isoformat() if inv.sent_at else None,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "error": inv.last_error,
            "secure_exam_link": secure_exam_link
        }

    @classmethod
    def send_reminder(
        cls,
        db: Session,
        invitation_id: str,
        current_user: User,
        provider_override: Optional[BaseEmailProvider] = None
    ) -> Dict[str, Any]:
        """Sends an exam reminder email for an active invitation."""
        inv = db.query(ExamInvitation).filter(ExamInvitation.id == invitation_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Exam invitation not found")

        assessment = inv.assessment
        if current_user.role != Role.PLATFORM_ADMIN and assessment.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to send reminders for another organization"
            )

        now_utc = datetime.now(timezone.utc)
        expires_at_utc = inv.expires_at.replace(tzinfo=timezone.utc) if inv.expires_at.tzinfo is None else inv.expires_at
        if now_utc > expires_at_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send reminder for an expired invitation. Please resend the invitation instead."
            )

        cand_inv = inv.candidate_invitation
        raw_token = cand_inv.invitation_token if cand_inv else None
        if not raw_token:
            # Recreate raw token if needed
            raw_token = generate_invitation_token()
            inv.invitation_token_hash = hash_token(raw_token)
            if cand_inv:
                cand_inv.invitation_token = raw_token

        secure_exam_link = cls.build_exam_link(raw_token)

        start_str = (
            assessment.start_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.start_time else "Available immediately"
        )
        end_str = (
            assessment.end_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            if assessment.end_time else "Open window until deadline"
        )

        org_name = assessment.organization.name if assessment.organization else "ProctorAI Assessment Platform"
        recruiter_name = current_user.full_name or "Assessment Coordinator"
        recruiter_email = current_user.email or settings.EMAIL_FROM_ADDRESS

        context = {
            "candidate_name": inv.recipient_name,
            "candidate_email": inv.recipient_email,
            "assessment_title": assessment.title,
            "assessment_description": assessment.description or "Comprehensive Technical Evaluation",
            "duration": f"{assessment.total_duration_minutes} minutes",
            "start_datetime": start_str,
            "end_datetime": end_str,
            "total_marks": str(assessment.total_marks),
            "passing_marks": f"{int((assessment.passing_percentage / 100.0) * assessment.total_marks)} ({assessment.passing_percentage}%)",
            "exam_instructions": assessment.instructions or "Please follow all proctoring guidelines during the test.",
            "secure_exam_link": secure_exam_link,
            "recruiter_name": recruiter_name,
            "recruiter_email": recruiter_email,
            "organization_name": org_name,
        }

        subject = render_exam_invitation_subject(assessment.title, is_reminder=True)
        html_body = render_exam_invitation_html(context, is_reminder=True)
        text_body = render_exam_invitation_text(context, is_reminder=True)

        provider = provider_override or get_email_provider()
        send_result = provider.send_email(
            to_email=inv.recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_email=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
            reply_to=recruiter_email
        )

        attempt = InvitationDeliveryAttempt(
            invitation_id=inv.id,
            attempt_type=DeliveryAttemptType.REMINDER,
            provider=send_result.provider,
            status=DeliveryAttemptStatus.ACCEPTED if send_result.success else DeliveryAttemptStatus.FAILED,
            provider_message_id=send_result.message_id,
            error_message=send_result.error,
            duration_ms=send_result.duration_ms
        )
        db.add(attempt)

        if send_result.success:
            inv.last_error = None
        else:
            inv.last_error = send_result.error

        db.commit()
        db.refresh(inv)

        return {
            "invitation_id": inv.id,
            "recipient_email": inv.recipient_email,
            "status": "REMINDER_SENT" if send_result.success else "REMINDER_FAILED",
            "provider_message_id": send_result.message_id,
            "error": send_result.error
        }

    @classmethod
    def validate_invitation_token(cls, db: Session, raw_token: str) -> Dict[str, Any]:
        """
        Public secure endpoint validating invitation token without leaking answers or credentials.
        Validates token hash, expiration, and assessment schedule window.
        """
        if not raw_token or not raw_token.strip():
            raise HTTPException(status_code=400, detail="Invitation token is required")

        token_hash = hash_token(raw_token.strip())

        # Lookup in exam_invitations first, fallback to candidate_invitations
        exam_inv = db.query(ExamInvitation).filter(
            ExamInvitation.invitation_token_hash == token_hash
        ).first()

        cand_inv = None
        if exam_inv:
            cand_inv = exam_inv.candidate_invitation
            assessment = exam_inv.assessment
            expires_at = exam_inv.expires_at
            recipient_name = exam_inv.recipient_name
            recipient_email = exam_inv.recipient_email
        else:
            # Fallback by raw token in candidate_invitations for backwards compatibility
            cand_inv = db.query(CandidateInvitation).filter(
                CandidateInvitation.invitation_token == raw_token.strip()
            ).first()
            if not cand_inv:
                raise HTTPException(status_code=404, detail="Invalid or unrecognized invitation token")
            assessment = cand_inv.assessment
            expires_at = cand_inv.expires_at
            recipient_name = cand_inv.full_name
            recipient_email = cand_inv.email

        now_utc = datetime.now(timezone.utc)
        expires_at_utc = expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at

        # Check expiration
        is_expired = now_utc > expires_at_utc

        # Check scheduling window
        schedule_status = "AVAILABLE"  # AVAILABLE | UPCOMING | EXPIRED | CLOSED
        time_until_start_seconds = 0
        if assessment.start_time:
            start_utc = assessment.start_time.replace(tzinfo=timezone.utc) if assessment.start_time.tzinfo is None else assessment.start_time
            if now_utc < start_utc:
                schedule_status = "UPCOMING"
                time_until_start_seconds = int((start_utc - now_utc).total_seconds())

        if assessment.end_time:
            end_utc = assessment.end_time.replace(tzinfo=timezone.utc) if assessment.end_time.tzinfo is None else assessment.end_time
            if now_utc > end_utc:
                schedule_status = "EXPIRED"

        if is_expired:
            schedule_status = "EXPIRED"

        candidate_status_str = cand_inv.status.value if cand_inv else "INVITED"
        attempt = cand_inv.attempt if cand_inv else None
        attempt_status_str = attempt.status.value if attempt else None

        rules = assessment.rules
        can_start = (
            schedule_status == "AVAILABLE"
            and not is_expired
            and candidate_status_str not in ("SUBMITTED", "DISQUALIFIED")
            and attempt_status_str not in ("SUBMITTED", "AUTO_SUBMITTED")
        )

        return {
            "valid": True,
            "assessment_id": assessment.id,
            "assessment_title": assessment.title,
            "assessment_description": assessment.description,
            "instructions": assessment.instructions,
            "duration_minutes": assessment.total_duration_minutes,
            "total_marks": assessment.total_marks,
            "passing_percentage": assessment.passing_percentage,
            "start_time": assessment.start_time.isoformat() if assessment.start_time else None,
            "end_time": assessment.end_time.isoformat() if assessment.end_time else None,
            "schedule_status": schedule_status,
            "time_until_start_seconds": time_until_start_seconds,
            "can_start": can_start,
            "expires_at": expires_at.isoformat(),
            "candidate_name": recipient_name,
            "candidate_email": recipient_email,
            "candidate_status": candidate_status_str,
            "attempt_status": attempt_status_str,
            "system_check_passed": cand_inv.system_check_passed if cand_inv else False,
            "proctoring_required": rules.webcam_proctoring_enabled if rules else True,
            "fullscreen_enforced": rules.full_screen_enforced if rules else True,
            "seb_required": rules.seb_required if rules else False,
        }

    @classmethod
    def handle_webhook(
        cls,
        db: Session,
        event_type: str,
        provider_message_id: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Updates delivery status from email provider webhook callback.
        Supports delivered, opened, bounced/failed events.
        """
        if not provider_message_id:
            return False

        inv = db.query(ExamInvitation).filter(
            ExamInvitation.provider_message_id == provider_message_id
        ).first()

        if not inv:
            logger.info("Webhook event '%s' received for unknown message_id '%s'", event_type, provider_message_id)
            return False

        now_utc = datetime.now(timezone.utc)
        normalized_event = event_type.lower()

        if "delivered" in normalized_event:
            inv.status = ExamInvitationStatus.DELIVERED
            inv.delivered_at = now_utc
        elif "open" in normalized_event or "opened" in normalized_event:
            inv.status = ExamInvitationStatus.OPENED
            inv.opened_at = now_utc
            if not inv.delivered_at:
                inv.delivered_at = now_utc
        elif "bounce" in normalized_event or "fail" in normalized_event:
            inv.status = ExamInvitationStatus.FAILED
            inv.last_error = error_message or f"Provider webhook reported delivery failure: {event_type}"

        db.commit()
        logger.info("Updated invitation '%s' to status '%s' via webhook", inv.id, inv.status.value)
        return True
