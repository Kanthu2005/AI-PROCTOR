from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Role
from app.models.attempt import Attempt, AttemptStatus
from app.models.assessment import Assessment
from app.models.proctoring import ProctoringIncident, ProctorReviewDecision, ProctoringEvidenceAccessAudit
from app.schemas.proctoring import (
    ProctoringEventIngest,
    ReviewIncidentRequest,
    ReviewerDecisionResponse,
    LiveProctorCandidateFeed,
    EvidenceAccessAuditResponse,
    PrivacyNoticeResponse,
    EvidencePurgeRequest,
    EvidencePurgeResponse
)
from app.services.proctoring_service import ProctoringService
from app.services.websocket_manager import live_proctor_manager
from app.dependencies import get_current_user, require_roles
from app.config import settings

router = APIRouter(prefix="/proctoring", tags=["AI Proctoring & Reviewer Workflow"])


@router.post("/attempts/{attempt_id}/events", response_model=Dict[str, Any])
async def ingest_proctoring_event(
    attempt_id: str,
    event_in: ProctoringEventIngest,
    db: Session = Depends(get_db)
):
    """
    Ingests client events (fullscreen exit, tab/window visibility change, devtools, copy/paste),
    hardware permission checks (camera/mic permission denied, device check passed),
    connection interruptions, or CV detections (face missing, multiple faces).
    
    Applies explainable rules, burst deduplication, risk scoring, and stores chronological risk history.
    Broadcasts real-time alert to connected proctors via WebSocket.
    """
    result = ProctoringService.ingest_event(db, attempt_id, event_in)

    # Real-time WebSocket broadcast to authorized proctors
    try:
        att = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if att:
            await live_proctor_manager.broadcast_to_proctors(att.assessment_id, {
                "type": "PROCTORING_INFRACTION",
                "attempt_id": attempt_id,
                "candidate_name": att.candidate_name,
                "event_type": result.get("event_type"),
                "risk_points": result.get("risk_points"),
                "current_risk_score": result.get("current_attempt_risk_score"),
                "current_risk_level": result.get("current_risk_level"),
                "is_deduplicated": result.get("is_deduplicated"),
                "explanation": result.get("explanation"),
                "disqualified": result.get("disqualified"),
                "disqualification_reason": result.get("disqualification_reason")
            })
    except Exception:
        pass

    return result


@router.post("/attempts/{attempt_id}/review", response_model=Dict[str, Any])
def review_flagged_attempt(
    attempt_id: str,
    review_in: ReviewIncidentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PROCTOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Proctor / Reviewer Decision Workflow:
    Reviewers evaluate candidate attempts and select:
    - VALID: Cleared candidate, legitimate test environment.
    - SUSPICIOUS: Flagged for elevated monitoring or escalation.
    - CONFIRMED_VIOLATION: Human reviewer confirms cheating; disqualifies candidate.
    - FALSE_POSITIVE: Overrides AI false alarm; clears candidate without penalty.
    
    Supports reviewer comments, escalation to Lead Proctor/Org Admin, and records decision history.
    """
    attempt_record = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt_record:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Enforce Organization Isolation
    if current_user.role != Role.PLATFORM_ADMIN and current_user.org_id:
        if attempt_record.assessment and attempt_record.assessment.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot review attempt belonging to another organization"
            )

    attempt = ProctoringService.review_incident(
        db=db,
        attempt_id=attempt_id,
        review_status=review_in.status,
        proctor_notes=review_in.proctor_notes,
        reviewer=current_user,
        is_escalated=bool(review_in.is_escalated),
        escalated_to_role=review_in.escalated_to_role,
        escalation_reason=review_in.escalation_reason
    )

    return {
        "attempt_id": attempt.id,
        "human_review_status": attempt.human_review_status.value,
        "proctor_notes": attempt.proctor_notes,
        "status": attempt.status.value,
        "is_escalated": attempt.is_escalated,
        "escalated_to_role": attempt.escalated_to_role,
        "disqualified_reason": attempt.disqualified_reason
    }


@router.get("/attempts/{attempt_id}/review-history", response_model=List[ReviewerDecisionResponse])
def get_attempt_review_history(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PROCTOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Retrieves full decision history and reviewer audit trail for an attempt.
    """
    attempt_record = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt_record:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if current_user.role != Role.PLATFORM_ADMIN and current_user.org_id:
        if attempt_record.assessment and attempt_record.assessment.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot view review history for another organization"
            )

    decisions = db.query(ProctorReviewDecision).filter(
        ProctorReviewDecision.attempt_id == attempt_id
    ).order_by(ProctorReviewDecision.created_at.desc()).all()

    return [
        ReviewerDecisionResponse(
            id=d.id,
            attempt_id=d.attempt_id,
            reviewer_id=d.reviewer_id,
            reviewer_name=d.reviewer.full_name if d.reviewer else None,
            decision=d.decision,
            comments=d.comments,
            is_escalated=d.is_escalated,
            escalated_to_role=d.escalated_to_role,
            escalation_reason=d.escalation_reason,
            risk_score_snapshot=d.risk_score_snapshot,
            rule_version=d.rule_version,
            created_at=d.created_at
        )
        for d in decisions
    ]


@router.get("/assessments/{assessment_id}/live-feed", response_model=List[Dict[str, Any]])
def get_assessment_live_feed(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PROCTOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Live dashboard feed of all candidate attempts for proctor monitoring console.
    Ordered by highest risk score first so proctors prioritize flagged sessions.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if current_user.role != Role.PLATFORM_ADMIN and current_user.org_id and assessment.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access live feed of another organization"
        )
    return ProctoringService.get_live_proctor_feed(db, assessment_id)


@router.get("/attempts/{attempt_id}/live-status")
def get_attempt_live_status(
    attempt_id: str,
    since: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PROCTOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Polling / reconnect fallback endpoint for live candidate monitoring.
    Used when WebSocket connection drops or firewall prevents persistent WebSockets.
    """
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if current_user.role != Role.PLATFORM_ADMIN and current_user.org_id:
        if attempt.assessment and attempt.assessment.org_id != current_user.org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    now_utc = datetime.now(timezone.utc)
    remaining_sec = 0
    if attempt.server_expiry_at:
        exp_utc = attempt.server_expiry_at.replace(tzinfo=timezone.utc) if attempt.server_expiry_at.tzinfo is None else attempt.server_expiry_at
        remaining_sec = max(0, int((exp_utc - now_utc).total_seconds()))

    incidents_query = db.query(ProctoringIncident).filter(ProctoringIncident.attempt_id == attempt_id)
    if since:
        incidents_query = incidents_query.filter(ProctoringIncident.occurred_at > since)
    incidents = incidents_query.order_by(ProctoringIncident.occurred_at.desc()).all()

    return {
        "attempt_id": attempt.id,
        "status": attempt.status.value,
        "risk_score": attempt.risk_score,
        "risk_level": attempt.risk_level.value,
        "human_review_status": attempt.human_review_status.value,
        "tab_switch_count": attempt.tab_switch_count,
        "remaining_seconds": remaining_sec,
        "is_escalated": attempt.is_escalated,
        "escalated_to_role": attempt.escalated_to_role,
        "new_incidents_count": len(incidents),
        "incidents": [
            {
                "id": inc.id,
                "event_type": inc.event_type.value,
                "severity": inc.severity.value,
                "risk_points": inc.risk_points,
                "occurred_at": inc.occurred_at.isoformat(),
                "is_deduplicated": inc.is_deduplicated
            }
            for inc in incidents
        ]
    }


@router.get("/attempts/{attempt_id}/incidents", response_model=List[Dict[str, Any]])
def get_attempt_incidents(
    attempt_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PROCTOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Returns granular contributing events and snapshot evidence for the evidence review modal.
    Logs an access audit entry to track who reviewed candidate evidence.
    """
    attempt_record = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt_record:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if current_user.role != Role.PLATFORM_ADMIN and current_user.org_id:
        if attempt_record.assessment and attempt_record.assessment.org_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access incidents of another organization"
            )

    # Log Evidence Access Audit
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    ProctoringService.log_evidence_access(
        db=db,
        attempt_id=attempt_id,
        user=current_user,
        action="EVIDENCE_LIST_VIEW",
        ip_address=client_ip,
        user_agent=user_agent
    )

    incidents = db.query(ProctoringIncident).filter(
        ProctoringIncident.attempt_id == attempt_id
    ).order_by(ProctoringIncident.occurred_at.desc()).all()

    return [
        {
            "id": inc.id,
            "event_type": inc.event_type.value,
            "severity": inc.severity.value,
            "risk_points": inc.risk_points,
            "metadata": inc.metadata_json,
            "snapshot_data": inc.snapshot_data,
            "evidence_ref": inc.evidence_ref,
            "is_deduplicated": inc.is_deduplicated,
            "occurred_at": inc.occurred_at.isoformat() if inc.occurred_at else None
        }
        for inc in incidents
    ]


@router.get("/attempts/{attempt_id}/evidence-access-audit", response_model=List[EvidenceAccessAuditResponse])
def get_attempt_evidence_access_audit(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PROCTOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Returns audit trail of all reviewers who accessed candidate evidence/snapshots.
    """
    attempt_record = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt_record:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if current_user.role != Role.PLATFORM_ADMIN and current_user.org_id:
        if attempt_record.assessment and attempt_record.assessment.org_id != current_user.org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    audits = db.query(ProctoringEvidenceAccessAudit).filter(
        ProctoringEvidenceAccessAudit.attempt_id == attempt_id
    ).order_by(ProctoringEvidenceAccessAudit.created_at.desc()).all()

    return [
        EvidenceAccessAuditResponse(
            id=a.id,
            attempt_id=a.attempt_id,
            incident_id=a.incident_id,
            user_id=a.user_id,
            user_email=a.user_email,
            user_role=a.user_role,
            action=a.action,
            ip_address=a.ip_address,
            created_at=a.created_at
        )
        for a in audits
    ]


@router.get("/privacy-notice", response_model=PrivacyNoticeResponse)
def get_proctoring_privacy_notice():
    """
    Public candidate privacy notice and proctoring explainability policy.
    Discloses collected telemetries, retention schedule, and human review guarantees.
    """
    return PrivacyNoticeResponse(
        title="ProctorAI Candidate Privacy Notice & Proctoring Transparency",
        data_collected=[
            "Camera video snapshots for presence verification (where enabled)",
            "Microphone ambient sound activity metrics",
            "Browser window blur and tab-switch timestamps",
            "Fullscreen entry and exit events",
            "Pre-test hardware check verification logs"
        ],
        purpose="Ensuring academic integrity and equal, fair assessment conditions for all candidates",
        ai_use_policy="AI predictions serve exclusively as prioritization signals for human reviewers. Candidates are never disqualified automatically solely based on AI flags or a single browser event.",
        retention_period_days=settings.PROCTORING_EVIDENCE_RETENTION_DAYS,
        candidate_rights="Candidates have the right to transparent explanations of flagged events and can request access audit logs or evidence purge upon assessment conclusion."
    )


@router.post("/evidence/purge", response_model=EvidencePurgeResponse)
def purge_expired_proctoring_evidence(
    purge_in: EvidencePurgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Configurable evidence retention and deletion:
    Wipes sensitive webcam base64 snapshots and evidence files older than retention policy (e.g. 30 days).
    Preserves anonymized risk logs for statistical scoring integrity.
    """
    res = ProctoringService.purge_expired_evidence(
        db=db,
        retention_days=purge_in.retention_days,
        assessment_id=purge_in.assessment_id
    )
    return EvidencePurgeResponse(
        purged_incidents_count=res["purged_incidents_count"],
        retention_cutoff=res["retention_cutoff"],
        message=res["message"]
    )
