from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Role
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.schemas.candidate import (
    BulkInviteRequest, BulkInviteResponse, CandidateInvitationResponse, CandidateSystemCheckRequest, CandidateInstructionsResponse
)
from app.services.invitation_service import InvitationService
from app.dependencies import get_current_user, require_roles, verify_tenant_access

router = APIRouter(prefix="/candidates", tags=["Candidate Management & Invitations"])

AUTHORIZED_INVITE_ROLES = [Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN]


@router.post("/bulk-invite", response_model=BulkInviteResponse, status_code=status.HTTP_201_CREATED)
def bulk_invite_candidates(
    invite_in: BulkInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_INVITE_ROLES))
):
    from app.models.assessment import Assessment
    assessment = db.query(Assessment).filter(Assessment.id == invite_in.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_tenant_access(assessment.org_id, current_user, db)

    invitations = InvitationService.bulk_invite_candidates(
        db,
        assessment_id=invite_in.assessment_id,
        candidates=invite_in.candidates,
        expires_in_hours=invite_in.expires_in_hours
    )
    return BulkInviteResponse(
        total_processed=len(invitations),
        invited_candidates=[CandidateInvitationResponse.model_validate(inv) for inv in invitations]
    )


@router.get("/invitations/{token}/verify", response_model=CandidateInvitationResponse)
def verify_invitation_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Public candidate entrypoint: verifies expiring invitation token,
    checks expiration timestamp, and transitions candidate status from INVITED to REGISTERED.
    """
    invitation = InvitationService.verify_invitation_token(db, token)
    return invitation


@router.get("/invitations/{token}/instructions", response_model=CandidateInstructionsResponse)
def get_candidate_instructions(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Returns candidate dashboard and assessment instructions, including timing, marks,
    rules (negative marking, navigation mode, proctoring requirements), and pre-check status.
    """
    return InvitationService.get_candidate_instructions(db, token)


@router.post("/invitations/{token}/system-check", response_model=CandidateInvitationResponse)
def perform_system_check(
    token: str,
    check_data: CandidateSystemCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Validates hardware and environment compatibility (camera, mic, browser, fullscreen).
    Upon passing, transitions candidate status to VERIFIED.
    """
    invitation = InvitationService.record_system_check(db, token, check_data)
    return invitation


@router.get("/assessments/{assessment_id}/invitations", response_model=List[CandidateInvitationResponse])
def list_assessment_invitations(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_INVITE_ROLES, Role.PROCTOR))
):
    from app.models.assessment import Assessment
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_tenant_access(assessment.org_id, current_user, db)
    return db.query(CandidateInvitation).filter(CandidateInvitation.assessment_id == assessment_id).all()


@router.get("", response_model=List[dict])
def list_all_candidates(
    org_id: str = None,
    assessment_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_INVITE_ROLES, Role.PROCTOR))
):
    query = db.query(CandidateInvitation)
    if current_user.role != Role.PLATFORM_ADMIN:
        if org_id:
            verify_tenant_access(org_id, current_user, db)
        query = query.filter(CandidateInvitation.org_id == current_user.org_id)
    elif org_id:
        query = query.filter(CandidateInvitation.org_id == org_id)

    if assessment_id:
        query = query.filter(CandidateInvitation.assessment_id == assessment_id)

    invitations = query.order_by(CandidateInvitation.created_at.desc()).all()
    results = []
    for inv in invitations:
        risk_level = "LOW"
        risk_score = 0
        total_score = None
        percentage = None
        is_passed = None
        is_result_released = False
        result_decision = None
        result_released_at = None
        recruiter_feedback = None

        if inv.attempt:
            risk_level = inv.attempt.risk_level.value
            risk_score = inv.attempt.risk_score
            total_score = inv.attempt.total_score
            percentage = inv.attempt.percentage
            is_passed = inv.attempt.is_passed
            is_result_released = getattr(inv.attempt, 'is_result_released', False)
            result_decision = getattr(inv.attempt, 'result_decision', None)
            result_released_at = inv.attempt.result_released_at.isoformat() if inv.attempt.result_released_at else None
            recruiter_feedback = getattr(inv.attempt, 'recruiter_feedback', None)

        results.append({
            "id": inv.id,
            "full_name": inv.full_name,
            "email": inv.email,
            "status": inv.status.value,
            "invitation_token": inv.invitation_token,
            "assessment_id": inv.assessment_id,
            "assessment_title": inv.assessment.title if inv.assessment else "Assessment",
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "attempt_id": inv.attempt.id if inv.attempt else None,
            "total_score": total_score,
            "percentage": percentage,
            "is_passed": is_passed,
            "is_result_released": is_result_released,
            "result_decision": result_decision,
            "result_released_at": result_released_at,
            "recruiter_feedback": recruiter_feedback
        })
    return results


@router.get("/me/invitations", response_model=List[dict])
def get_my_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns assessments and invitations assigned to the currently logged in candidate.
    Scores, percentages, and pass/fail states are strictly hidden until released by recruiter.
    """
    query = db.query(CandidateInvitation).filter(
        CandidateInvitation.email == current_user.email.lower()
    )
    invitations = query.order_by(CandidateInvitation.created_at.desc()).all()

    results = []
    for inv in invitations:
        risk_level = None
        risk_score = None
        score = None
        is_passed = None
        is_released = False
        result_decision = "PENDING_REVIEW"
        recruiter_feedback = None

        if inv.attempt:
            # Check individual release on attempt OR global assessment release
            is_released = bool(
                getattr(inv.attempt, 'is_result_released', False) or
                (inv.assessment and getattr(inv.assessment, 'is_results_released', False))
            )
            if is_released:
                score = inv.attempt.total_score
                is_passed = (inv.attempt.result_decision == "PASSED") if getattr(inv.attempt, 'result_decision', None) else inv.attempt.is_passed
                result_decision = getattr(inv.attempt, 'result_decision', None) or ("PASSED" if is_passed else "COMPLETED")
                recruiter_feedback = getattr(inv.attempt, 'recruiter_feedback', None)

        results.append({
            "id": inv.id,
            "full_name": inv.full_name,
            "email": inv.email,
            "status": inv.status.value,
            "invitation_token": inv.invitation_token,
            "assessment_id": inv.assessment_id,
            "assessment_title": inv.assessment.title if inv.assessment else "Assessment",
            "duration_minutes": inv.assessment.total_duration_minutes if inv.assessment else 90,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "attempt_id": inv.attempt.id if inv.attempt else None,
            "total_score": score,
            "is_passed": is_passed,
            "is_result_released": is_released,
            "result_decision": result_decision,
            "recruiter_feedback": recruiter_feedback
        })
    return results


@router.post("/invite", response_model=dict)
def invite_single_candidate(
    invite_in: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_INVITE_ROLES))
):
    from app.models.assessment import Assessment
    assessment = db.query(Assessment).filter(Assessment.id == invite_in["assessment_id"]).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_tenant_access(assessment.org_id, current_user, db)

    from app.schemas.candidate import CandidateInviteItem
    invitation = InvitationService.bulk_invite_candidates(
        db,
        assessment_id=invite_in["assessment_id"],
        candidates=[CandidateInviteItem(email=invite_in["email"], full_name=invite_in["full_name"])],
        expires_in_hours=int(invite_in.get("expires_in_hours", 72))
    )[0]
    return {
        "id": invitation.id,
        "full_name": invitation.full_name,
        "email": invitation.email,
        "invitation_token": invitation.invitation_token,
        "assessment_id": invitation.assessment_id,
        "status": invitation.status.value
    }


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_200_OK)
def revoke_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_INVITE_ROLES))
):
    invitation = db.query(CandidateInvitation).filter(CandidateInvitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    verify_tenant_access(invitation.org_id, current_user, db)
    
    InvitationService.revoke_invitation(db, invitation_id)
    return {"message": "Invitation successfully revoked", "invitation_id": invitation_id}


@router.post("/invitations/{invitation_id}/resend", response_model=dict)
def resend_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_INVITE_ROLES))
):
    invitation = db.query(CandidateInvitation).filter(CandidateInvitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    verify_tenant_access(invitation.org_id, current_user, db)

    refreshed_inv = InvitationService.resend_invitation(db, invitation_id)
    return {
        "id": refreshed_inv.id,
        "full_name": refreshed_inv.full_name,
        "email": refreshed_inv.email,
        "invitation_token": refreshed_inv.invitation_token,
        "assessment_id": refreshed_inv.assessment_id,
        "status": refreshed_inv.status.value,
        "expires_at": refreshed_inv.expires_at.isoformat() if refreshed_inv.expires_at else None
    }

