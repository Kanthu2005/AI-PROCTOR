from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.assessment import Assessment
from app.schemas.candidate import CandidateInviteItem, CandidateSystemCheckRequest
from app.utils.security import generate_invitation_token, is_demo_replayable_token


class InvitationService:
    @staticmethod
    def bulk_invite_candidates(
        db: Session,
        assessment_id: str,
        candidates: List[CandidateInviteItem],
        expires_in_hours: int = 72
    ) -> List[CandidateInvitation]:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        expiry_time = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        created_invitations = []

        for c in candidates:
            # Check if active invitation already exists for this email & assessment
            existing = db.query(CandidateInvitation).filter(
                CandidateInvitation.assessment_id == assessment_id,
                CandidateInvitation.email == c.email.lower()
            ).first()

            if existing:
                # Update expiration if needed
                existing.expires_at = expiry_time
                existing.full_name = c.full_name
                created_invitations.append(existing)
            else:
                token = generate_invitation_token()
                inv = CandidateInvitation(
                    assessment_id=assessment_id,
                    org_id=assessment.org_id,
                    email=c.email.lower(),
                    full_name=c.full_name,
                    invitation_token=token,
                    expires_at=expiry_time,
                    status=CandidateStatus.INVITED,
                    system_check_passed=False
                )
                db.add(inv)
                created_invitations.append(inv)

        db.commit()
        for inv in created_invitations:
            db.refresh(inv)
        return created_invitations

    @staticmethod
    def verify_invitation_token(db: Session, token: str) -> CandidateInvitation:
        invitation = db.query(CandidateInvitation).filter(
            CandidateInvitation.invitation_token == token
        ).first()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invalid invitation token")

        now_utc = datetime.now(timezone.utc)
        expires_at_utc = invitation.expires_at.replace(tzinfo=timezone.utc) if invitation.expires_at.tzinfo is None else invitation.expires_at

        if now_utc > expires_at_utc:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation link has expired"
            )

        if invitation.status == CandidateStatus.DISQUALIFIED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidate is disqualified from this assessment"
            )

        if invitation.status == CandidateStatus.SUBMITTED:
            if is_demo_replayable_token(invitation.invitation_token):
                invitation.status = CandidateStatus.REGISTERED
                invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
                db.commit()
                db.refresh(invitation)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assessment has already been submitted"
                )

        # If still in INVITED status, mark as REGISTERED upon token access
        if invitation.status == CandidateStatus.INVITED:
            invitation.status = CandidateStatus.REGISTERED
            db.commit()
            db.refresh(invitation)

        return invitation

    @staticmethod
    def get_candidate_instructions(db: Session, token: str) -> dict:
        invitation = InvitationService.verify_invitation_token(db, token)
        assessment = invitation.assessment
        rules = assessment.rules
        attempt = invitation.attempt

        return {
            "invitation_id": invitation.id,
            "assessment_id": assessment.id,
            "assessment_title": assessment.title,
            "description": assessment.description,
            "instructions": assessment.instructions,
            "duration_minutes": assessment.total_duration_minutes,
            "total_marks": assessment.total_marks,
            "passing_percentage": assessment.passing_percentage,
            "rules": {
                "navigation_mode": rules.navigation_mode.value if rules else "FREE",
                "negative_marking_enabled": rules.negative_marking_enabled if rules else True,
                "full_screen_enforced": rules.full_screen_enforced if rules else True,
                "webcam_proctoring_enabled": rules.webcam_proctoring_enabled if rules else True,
                "max_tab_switches_allowed": rules.max_tab_switches_allowed if rules else 3,
                "copy_paste_blocked": rules.copy_paste_blocked if rules else True,
                "randomize_questions": rules.randomize_questions if rules else False,
                "randomize_options": rules.randomize_options if rules else False,
                "seb_required": rules.seb_required if rules else False
            },
            "seb": {
                "required": bool(rules and rules.seb_required),
                "config_url": f"/api/v1/seb/invitations/{invitation.invitation_token}/config.seb" if (rules and rules.seb_required) else None,
                "launch_scheme_url": f"sebs://localhost/api/v1/seb/invitations/{invitation.invitation_token}/config.seb" if (rules and rules.seb_required) else None,
                "supported_platforms": ["Windows", "macOS", "iOS"],
                "lockdown_required": bool(rules and rules.seb_required)
            },
            "candidate_name": invitation.full_name,
            "candidate_email": invitation.email,
            "expires_at": invitation.expires_at,
            "status": invitation.status,
            "system_check_passed": invitation.system_check_passed,
            "attempt_status": attempt.status.value if attempt else None,
            "attempt_id": attempt.id if attempt else None,
            "submission_receipt": attempt.submission_receipt if attempt else None
        }

    @staticmethod
    def record_system_check(
        db: Session,
        token: str,
        check_data: CandidateSystemCheckRequest
    ) -> CandidateInvitation:
        invitation = InvitationService.verify_invitation_token(db, token)

        if not (check_data.camera_ok and check_data.microphone_ok and check_data.browser_compatible and check_data.fullscreen_supported):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All system compatibility criteria (camera, mic, browser, fullscreen) must pass before starting"
            )

        invitation.system_check_passed = True
        invitation.status = CandidateStatus.VERIFIED
        if check_data.face_snapshot_base64:
            invitation.verified_face_reference = check_data.face_snapshot_base64[:500]  # Store reference snapshot

        db.commit()
        db.refresh(invitation)
        return invitation

    @staticmethod
    def transition_status(db: Session, invitation_id: str, new_status: CandidateStatus) -> CandidateInvitation:
        invitation = db.query(CandidateInvitation).filter(CandidateInvitation.id == invitation_id).first()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        invitation.status = new_status
        db.commit()
        db.refresh(invitation)
        return invitation

    @staticmethod
    def invite_single_candidate(
        db: Session,
        assessment_id: str,
        email: str,
        full_name: str,
        expires_in_hours: int = 72
    ) -> CandidateInvitation:
        res = InvitationService.bulk_invite_candidates(
            db,
            assessment_id=assessment_id,
            candidates=[CandidateInviteItem(email=email, full_name=full_name)],
            expires_in_hours=expires_in_hours
        )
        return res[0]

    @staticmethod
    def revoke_invitation(db: Session, invitation_id: str) -> bool:
        inv = db.query(CandidateInvitation).filter(CandidateInvitation.id == invitation_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found")
        db.delete(inv)
        db.commit()
        return True

    @staticmethod
    def resend_invitation(db: Session, invitation_id: str, expires_in_hours: int = 72) -> CandidateInvitation:
        inv = db.query(CandidateInvitation).filter(CandidateInvitation.id == invitation_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found")
        inv.invitation_token = generate_invitation_token()
        inv.expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        inv.status = CandidateStatus.INVITED
        inv.system_check_passed = False
        db.commit()
        db.refresh(inv)
        return inv

