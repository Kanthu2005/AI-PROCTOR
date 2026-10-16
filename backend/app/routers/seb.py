from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.assessment import Assessment
from app.models.candidate import CandidateInvitation
from app.services.seb_service import SafeExamBrowserService
from app.schemas.seb import (
    SEBClientDiagnosticRequest,
    SEBClientDiagnosticResponse,
    SEBLaunchInfoResponse,
    SEBQuitResponse
)

router = APIRouter(prefix="/seb", tags=["Safe Exam Browser Secure Mode"])


@router.get("/assessments/{assessment_id}/config.seb")
def download_assessment_seb_config(
    assessment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Downloads the official XML property list configuration (.seb file) for an assessment.
    Can be loaded directly into Safe Exam Browser to launch the exam in locked-down kiosk mode.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    base_url = str(request.base_url).rstrip("/")
    xml_data = SafeExamBrowserService.generate_seb_config_xml(assessment, base_url=base_url)

    return Response(
        content=xml_data,
        media_type="application/seb",
        headers={
            "Content-Disposition": f'attachment; filename="assessment_{assessment_id[:8]}.seb"',
            "Cache-Control": "no-store, no-cache, must-revalidate"
        }
    )


@router.get("/invitations/{token}/config.seb")
def download_candidate_seb_config(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Downloads a candidate-specific .seb configuration file containing their personalized
    invitation token in the startURL.
    """
    invitation = db.query(CandidateInvitation).filter(
        CandidateInvitation.invitation_token == token
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    base_url = str(request.base_url).rstrip("/")
    xml_data = SafeExamBrowserService.generate_seb_config_xml(
        invitation.assessment,
        invitation=invitation,
        base_url=base_url
    )

    return Response(
        content=xml_data,
        media_type="application/seb",
        headers={
            "Content-Disposition": f'attachment; filename="proctorai_exam_{invitation.id[:8]}.seb"',
            "Cache-Control": "no-store, no-cache, must-revalidate"
        }
    )


@router.get("/assessments/{assessment_id}/launch-info", response_model=SEBLaunchInfoResponse)
def get_assessment_launch_info(
    assessment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Returns download URLs and custom sebs:// protocol links to launch Safe Exam Browser.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    base_url = str(request.base_url).rstrip("/")
    return SafeExamBrowserService.generate_launch_info(assessment, base_url=base_url)


@router.get("/invitations/{token}/launch-info", response_model=SEBLaunchInfoResponse)
def get_candidate_launch_info(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Returns candidate-tailored launch URLs and protocol links for Safe Exam Browser.
    """
    invitation = db.query(CandidateInvitation).filter(
        CandidateInvitation.invitation_token == token
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    base_url = str(request.base_url).rstrip("/")
    return SafeExamBrowserService.generate_launch_info(
        invitation.assessment,
        invitation=invitation,
        base_url=base_url
    )


@router.post("/verify-client", response_model=SEBClientDiagnosticResponse)
def verify_seb_client(
    request: Request,
    body: Optional[SEBClientDiagnosticRequest] = None,
    seb_request_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-RequestHash"),
    seb_config_key_hash: Optional[str] = Header(None, alias="X-SafeExamBrowser-ConfigKeyHash"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    db: Session = Depends(get_db)
):
    """
    Pre-flight diagnostic endpoint: validates whether a candidate's Safe Exam Browser client
    is authentic and possesses the matching Browser Exam Key or Config Key.
    Provides immediate actionable feedback prior to launching the official attempt.
    """
    assessment_id = body.assessment_id if body else None
    token = body.invitation_token if body else None

    # Resolve assessment
    assessment = None
    if token:
        inv = db.query(CandidateInvitation).filter(CandidateInvitation.invitation_token == token).first()
        if inv:
            assessment = inv.assessment
    elif assessment_id:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()

    if not assessment:
        raise HTTPException(status_code=400, detail="Must provide either assessment_id or invitation_token for SEB verification")

    req_url = (body.request_url if body and body.request_url else str(request.url))
    req_hash = (seb_request_hash or (body.seb_request_hash if body else None))
    ck_hash = (seb_config_key_hash or (body.seb_config_key_hash if body else None))
    ua = (body.user_agent if (body and body.user_agent) else (user_agent if user_agent != "testclient" else None))

    result = SafeExamBrowserService.verify_seb_request(
        assessment=assessment,
        request_url=req_url,
        request_hash=req_hash,
        config_key_hash=ck_hash,
        user_agent=ua
    )

    return SEBClientDiagnosticResponse(
        is_seb_verified=result.is_valid,
        verification_mechanism=result.mechanism,
        platform_detected=result.platform,
        matched_key_type=result.matched_key_type,
        failure_reason=None if result.is_valid else result.detail,
        lockdown_guaranteed=result.lockdown_guaranteed
    )


@router.get("/quit", response_model=SEBQuitResponse)
def seb_quit_page():
    """
    Landing page for candidates exiting Safe Exam Browser after completing an exam.
    """
    return SEBQuitResponse(
        message="Assessment complete. You may safely quit Safe Exam Browser.",
        can_quit=True,
        quit_url="/api/v1/seb/quit"
    )
