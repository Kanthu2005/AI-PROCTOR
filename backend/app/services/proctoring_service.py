from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from app.config import settings
from app.models.attempt import Attempt, AttemptStatus, RiskLevel, HumanReviewStatus
from app.models.candidate import CandidateStatus
from app.models.proctoring import (
    ProctoringIncident, EventType, IncidentSeverity, ProctorReviewDecision, ProctoringEvidenceAccessAudit
)
from app.models.user import User
from app.schemas.proctoring import ProctoringEventIngest
from app.utils.cv_proctor import CVProctorEngine

logger = logging.getLogger("proctorai.proctoring")

EVENT_RISK_CONFIG: Dict[EventType, Dict[str, Any]] = {
    EventType.TAB_SWITCH: {
        "points": 15.0,
        "severity": IncidentSeverity.MEDIUM,
        "explanation": "Browser tab switched away from assessment window (rule: tab_switch_v1)",
        "dedup_window_seconds": 3,
    },
    EventType.VISIBILITY_CHANGE: {
        "points": 15.0,
        "severity": IncidentSeverity.MEDIUM,
        "explanation": "Assessment window visibility changed or blurred (rule: visibility_blur_v1)",
        "dedup_window_seconds": 3,
    },
    EventType.FULLSCREEN_EXIT: {
        "points": 20.0,
        "severity": IncidentSeverity.MEDIUM,
        "explanation": "Candidate exited full screen mode (rule: fullscreen_exit_v1)",
        "dedup_window_seconds": 5,
    },
    EventType.DEVTOOLS_OPEN: {
        "points": 40.0,
        "severity": IncidentSeverity.CRITICAL,
        "explanation": "Developer tools / inspect window opened (rule: devtools_tamper_v1)",
        "dedup_window_seconds": 5,
    },
    EventType.COPY_PASTE_ATTEMPT: {
        "points": 10.0,
        "severity": IncidentSeverity.LOW,
        "explanation": "Unauthorized copy or paste action intercepted (rule: clipboard_v1)",
        "dedup_window_seconds": 2,
    },
    EventType.CAMERA_PERMISSION_DENIED: {
        "points": 35.0,
        "severity": IncidentSeverity.HIGH,
        "explanation": "Webcam access denied or revoked by candidate (rule: hardware_perm_v1)",
        "dedup_window_seconds": 10,
    },
    EventType.MIC_PERMISSION_DENIED: {
        "points": 25.0,
        "severity": IncidentSeverity.MEDIUM,
        "explanation": "Microphone access denied or revoked by candidate (rule: hardware_perm_v1)",
        "dedup_window_seconds": 10,
    },
    EventType.CAMERA_DISCONNECTED: {
        "points": 25.0,
        "severity": IncidentSeverity.HIGH,
        "explanation": "Webcam video feed disconnected or hardware unavailable (rule: hardware_conn_v1)",
        "dedup_window_seconds": 10,
    },
    EventType.CAMERA_INTERRUPTED: {
        "points": 20.0,
        "severity": IncidentSeverity.MEDIUM,
        "explanation": "Webcam stream interrupted or stalled (rule: hardware_conn_v1)",
        "dedup_window_seconds": 10,
    },
    EventType.CONNECTION_INTERRUPTED: {
        "points": 10.0,
        "severity": IncidentSeverity.LOW,
        "explanation": "Candidate internet connection dropped or timed out (rule: network_conn_v1)",
        "dedup_window_seconds": 10,
    },
    EventType.CONNECTION_RESTORED: {
        "points": 0.0,
        "severity": IncidentSeverity.LOW,
        "explanation": "Candidate internet connection re-established (rule: network_conn_v1)",
        "dedup_window_seconds": 5,
    },
    EventType.DEVICE_CHECK_PASSED: {
        "points": 0.0,
        "severity": IncidentSeverity.LOW,
        "explanation": "Pre-test device and permission check completed successfully",
        "dedup_window_seconds": 5,
    },
    EventType.FACE_PRESENT: {
        "points": 0.0,
        "severity": IncidentSeverity.LOW,
        "explanation": "Candidate face confirmed present in camera frame",
        "dedup_window_seconds": 5,
    },
    EventType.FACE_MISSING: {
        "points": 10.0,
        "severity": IncidentSeverity.LOW,
        "explanation": "Candidate face not detected in webcam feed (rule: face_absence_v1)",
        "dedup_window_seconds": 5,
    },
    EventType.MULTIPLE_FACES: {
        "points": 30.0,
        "severity": IncidentSeverity.HIGH,
        "explanation": "Multiple faces detected simultaneously in candidate camera feed (rule: multi_face_v1)",
        "dedup_window_seconds": 5,
    },
    EventType.VOICE_DETECTED: {
        "points": 15.0,
        "severity": IncidentSeverity.LOW,
        "explanation": "Background speech or voice activity detected during silence window (rule: audio_voice_v1)",
        "dedup_window_seconds": 5,
    },
}


class ProctoringService:
    @staticmethod
    def calculate_risk_level(score: float) -> RiskLevel:
        if score < 25.0:
            return RiskLevel.LOW
        elif score <= 50.0:
            return RiskLevel.MEDIUM
        elif score <= 75.0:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    @staticmethod
    def ingest_event(
        db: Session,
        attempt_id: str,
        event_in: ProctoringEventIngest
    ) -> Dict[str, Any]:
        # 1. Validation & Event Spoofing Prevention
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        now_utc = datetime.now(timezone.utc)

        # Reject events for completed or unstarted attempts
        if attempt.status in (AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.TIMED_OUT):
            raise HTTPException(status_code=400, detail="Cannot ingest proctoring events for completed assessment attempt")
        if attempt.status == AttemptStatus.NOT_STARTED:
            raise HTTPException(status_code=400, detail="Attempt has not started yet")

        if attempt.status == AttemptStatus.DISQUALIFIED:
            return {
                "id": "disqualified",
                "attempt_id": attempt.id,
                "event_type": event_in.event_type.value,
                "severity": IncidentSeverity.CRITICAL.value,
                "risk_points": 0.0,
                "metadata_json": event_in.metadata,
                "occurred_at": now_utc,
                "current_attempt_risk_score": attempt.risk_score,
                "current_risk_level": attempt.risk_level.value,
                "disqualified": True,
                "disqualification_reason": attempt.disqualified_reason,
                "is_deduplicated": False,
                "explanation": "Attempt is already disqualified"
            }

        # Validate client timestamp against clock spoofing
        if event_in.client_timestamp:
            ts_utc = event_in.client_timestamp.replace(tzinfo=timezone.utc) if event_in.client_timestamp.tzinfo is None else event_in.client_timestamp
            drift_seconds = (ts_utc - now_utc).total_seconds()
            if drift_seconds > 60:
                raise HTTPException(
                    status_code=400,
                    detail=f"Event timestamp spoofing detected: timestamp is {int(drift_seconds)}s in the future"
                )
            if drift_seconds < -7200:
                raise HTTPException(
                    status_code=400,
                    detail="Event timestamp is excessively stale (> 2 hours old)"
                )

        # 2. Check CV proctoring if snapshot is provided
        cv_result = None
        if event_in.snapshot_base64:
            cv_result = CVProctorEngine.analyze_frame(event_in.snapshot_base64)
            if cv_result.get("infraction_detected"):
                detected_status = cv_result.get("status")
                if detected_status == "FACE_MISSING":
                    event_in.event_type = EventType.FACE_MISSING
                elif detected_status == "MULTIPLE_FACES":
                    event_in.event_type = EventType.MULTIPLE_FACES

        cfg = EVENT_RISK_CONFIG.get(event_in.event_type, {
            "points": 10.0,
            "severity": IncidentSeverity.LOW,
            "explanation": f"Generic proctoring alert: {event_in.event_type.value}",
            "dedup_window_seconds": settings.PROCTORING_DEDUP_WINDOW_SECONDS
        })

        # 3. Event Deduplication
        is_deduplicated = False
        dedup_reason = None

        # A. Deduplication by explicit client_event_id
        if event_in.client_event_id:
            existing_event = db.query(ProctoringIncident).filter(
                ProctoringIncident.attempt_id == attempt.id,
                ProctoringIncident.client_event_id == event_in.client_event_id
            ).first()
            if existing_event:
                logger.info(f"Duplicate client event ID received: {event_in.client_event_id}")
                return {
                    "id": existing_event.id,
                    "attempt_id": attempt.id,
                    "event_type": existing_event.event_type.value,
                    "severity": existing_event.severity.value,
                    "risk_points": 0.0,
                    "metadata_json": existing_event.metadata_json,
                    "occurred_at": existing_event.occurred_at,
                    "current_attempt_risk_score": attempt.risk_score,
                    "current_risk_level": attempt.risk_level.value,
                    "disqualified": (attempt.status == AttemptStatus.DISQUALIFIED),
                    "disqualification_reason": attempt.disqualified_reason,
                    "is_deduplicated": True,
                    "explanation": f"Deduplicated: event with ID {event_in.client_event_id} already ingested",
                    "rule_version": settings.PROCTORING_RULE_VERSION
                }

        # B. Sliding-window deduplication for rapid bursts (applies when client_timestamp or dedup flag is provided)
        dedup_window = cfg.get("dedup_window_seconds", settings.PROCTORING_DEDUP_WINDOW_SECONDS)
        should_check_window = (event_in.client_timestamp is not None) or event_in.metadata.get("check_dedup", False)

        if should_check_window:
            last_same_incident = db.query(ProctoringIncident).filter(
                ProctoringIncident.attempt_id == attempt.id,
                ProctoringIncident.event_type == event_in.event_type
            ).order_by(ProctoringIncident.occurred_at.desc()).first()

            if last_same_incident and last_same_incident.occurred_at:
                ref_time = event_in.client_timestamp if event_in.client_timestamp else now_utc
                ref_utc = ref_time.replace(tzinfo=timezone.utc) if ref_time.tzinfo is None else ref_time
                last_time = last_same_incident.occurred_at.replace(tzinfo=timezone.utc) if last_same_incident.occurred_at.tzinfo is None else last_same_incident.occurred_at
                elapsed = abs((ref_utc - last_time).total_seconds())
                if elapsed < dedup_window:
                    is_deduplicated = True
                    dedup_reason = f"Burst coalescing: repeated {event_in.event_type.value} within {dedup_window}s window ({elapsed:.1f}s elapsed)"

        # 4. Risk Points & Counter Calculation
        points = 0.0 if is_deduplicated else cfg["points"]
        severity = cfg["severity"]
        explanation = dedup_reason if is_deduplicated else cfg["explanation"]

        if not is_deduplicated:
            if event_in.event_type == EventType.TAB_SWITCH:
                attempt.tab_switch_count += 1

            # Accumulate dynamic risk score
            attempt.risk_score = round(attempt.risk_score + points, 1)
            attempt.risk_level = ProctoringService.calculate_risk_level(attempt.risk_score)

        # Record chronological risk history with explainable rule version
        if attempt.risk_history is None:
            attempt.risk_history = []
        history_entry = {
            "timestamp": now_utc.isoformat(),
            "event_type": event_in.event_type.value,
            "delta_points": points,
            "new_risk_score": attempt.risk_score,
            "new_risk_level": attempt.risk_level.value,
            "explanation": explanation,
            "rule_version": settings.PROCTORING_RULE_VERSION,
            "deduplicated": is_deduplicated
        }
        attempt.risk_history = list(attempt.risk_history) + [history_entry]

        # 5. Enforce explicit tab switch boundary if configured
        assessment = attempt.assessment
        rules = assessment.rules if assessment else None
        max_tabs = rules.max_tab_switches_allowed if rules else 3

        disqualified = False
        disqualification_reason = None

        if attempt.tab_switch_count > max_tabs:
            attempt.status = AttemptStatus.DISQUALIFIED
            disqualification_reason = f"Exceeded maximum allowed tab switches (limit: {max_tabs}, reached: {attempt.tab_switch_count})"
            attempt.disqualified_reason = disqualification_reason
            disqualified = True
            if attempt.invitation:
                attempt.invitation.status = CandidateStatus.DISQUALIFIED

        # 6. Create PostgreSQL incident record
        incident = ProctoringIncident(
            attempt_id=attempt.id,
            client_event_id=event_in.client_event_id,
            event_type=event_in.event_type,
            severity=severity,
            risk_points=points,
            metadata_json={
                **event_in.metadata,
                "cv_analysis": cv_result,
                "deduplicated": is_deduplicated,
                "rule_version": settings.PROCTORING_RULE_VERSION
            } if cv_result else {
                **event_in.metadata,
                "deduplicated": is_deduplicated,
                "rule_version": settings.PROCTORING_RULE_VERSION
            },
            snapshot_data=event_in.snapshot_base64[:200] if event_in.snapshot_base64 else None,
            evidence_ref=event_in.evidence_ref,
            is_deduplicated=is_deduplicated,
            occurred_at=now_utc
        )
        db.add(incident)
        db.commit()
        return {
            "id": incident.id,
            "attempt_id": attempt.id,
            "event_type": incident.event_type.value,
            "severity": incident.severity.value,
            "risk_points": incident.risk_points,
            "metadata_json": incident.metadata_json,
            "occurred_at": incident.occurred_at,
            "current_attempt_risk_score": attempt.risk_score,
            "current_risk_level": attempt.risk_level.value,
            "disqualified": disqualified,
            "disqualification_reason": disqualification_reason,
            "is_deduplicated": is_deduplicated,
            "explanation": explanation,
            "rule_version": settings.PROCTORING_RULE_VERSION
        }

    @staticmethod
    def review_incident(
        db: Session,
        attempt_id: str,
        review_status: HumanReviewStatus,
        proctor_notes: Optional[str] = None,
        reviewer: Optional[User] = None,
        is_escalated: bool = False,
        escalated_to_role: Optional[str] = None,
        escalation_reason: Optional[str] = None
    ) -> Attempt:
        """
        Reviewer Decision Workflow:
        Labels flagged attempts as VALID, SUSPICIOUS, CONFIRMED_VIOLATION, or FALSE_POSITIVE.
        Records reviewer comments, decision history, and escalation status.
        Never auto-disqualifies solely on AI predictions; requires confirmed human verdict.
        """
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        now_utc = datetime.now(timezone.utc)
        attempt.human_review_status = review_status
        if proctor_notes:
            attempt.proctor_notes = proctor_notes

        # Handle decisions explicitly
        if review_status == HumanReviewStatus.CONFIRMED_VIOLATION:
            attempt.status = AttemptStatus.DISQUALIFIED
            attempt.disqualified_reason = f"Proctor confirmed security violation: {proctor_notes or 'Proctor decision'}"
            if attempt.invitation:
                attempt.invitation.status = CandidateStatus.DISQUALIFIED
        elif review_status == HumanReviewStatus.FALSE_POSITIVE:
            # Clear or override AI flag; log explanation
            if attempt.risk_history is None:
                attempt.risk_history = []
            override_entry = {
                "timestamp": now_utc.isoformat(),
                "event_type": "HUMAN_REVIEW_OVERRIDE",
                "delta_points": 0.0,
                "new_risk_score": attempt.risk_score,
                "new_risk_level": attempt.risk_level.value,
                "explanation": f"Reviewer marked infractions as FALSE_POSITIVE: {proctor_notes or 'Legitimate candidate activity'}",
                "rule_version": settings.PROCTORING_RULE_VERSION,
                "deduplicated": False
            }
            attempt.risk_history = list(attempt.risk_history) + [override_entry]
        elif review_status == HumanReviewStatus.SUSPICIOUS:
            # Flag for elevated monitoring / secondary review
            pass

        # Handle Escalation
        if is_escalated:
            attempt.is_escalated = True
            attempt.escalated_to_role = escalated_to_role or "LEAD_PROCTOR"

        # Create persistent decision log
        decision_log = ProctorReviewDecision(
            attempt_id=attempt.id,
            reviewer_id=reviewer.id if reviewer else None,
            decision=review_status.value,
            comments=proctor_notes,
            is_escalated=is_escalated,
            escalated_to_role=escalated_to_role,
            escalation_reason=escalation_reason,
            risk_score_snapshot=attempt.risk_score,
            rule_version=settings.PROCTORING_RULE_VERSION
        )
        db.add(decision_log)

        db.commit()
        db.refresh(attempt)
        return attempt

    @staticmethod
    def log_evidence_access(
        db: Session,
        attempt_id: str,
        user: User,
        incident_id: Optional[str] = None,
        action: str = "EVIDENCE_VIEW",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ProctoringEvidenceAccessAudit:
        """
        Creates an audit record whenever reviewer views evidence/snapshots.
        """
        audit = ProctoringEvidenceAccessAudit(
            attempt_id=attempt_id,
            incident_id=incident_id,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
            org_id=user.org_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    @staticmethod
    def get_live_proctor_feed(db: Session, assessment_id: str) -> List[Dict[str, Any]]:
        """
        Returns active candidate attempt telemetry for proctor dashboard,
        ordered by highest risk score first (prioritization signals).
        """
        attempts = db.query(Attempt).filter(
            Attempt.assessment_id == assessment_id
        ).order_by(Attempt.risk_score.desc()).all()

        now_utc = datetime.now(timezone.utc)
        results = []

        for att in attempts:
            remaining_sec = 0
            if att.server_expiry_at:
                exp_utc = att.server_expiry_at.replace(tzinfo=timezone.utc) if att.server_expiry_at.tzinfo is None else att.server_expiry_at
                remaining_sec = max(0, int((exp_utc - now_utc).total_seconds()))

            last_incident = db.query(ProctoringIncident).filter(
                ProctoringIncident.attempt_id == att.id
            ).order_by(ProctoringIncident.occurred_at.desc()).first()

            results.append({
                "attempt_id": att.id,
                "candidate_name": att.candidate_name,
                "candidate_email": att.candidate_email,
                "assessment_title": att.assessment.title if att.assessment else "",
                "status": att.status.value,
                "remaining_seconds": remaining_sec,
                "risk_score": att.risk_score,
                "risk_level": att.risk_level.value,
                "human_review_status": att.human_review_status.value,
                "total_violations": len(att.incidents),
                "tab_switch_count": att.tab_switch_count,
                "is_escalated": att.is_escalated,
                "escalated_to_role": att.escalated_to_role,
                "disqualified_reason": att.disqualified_reason,
                "last_event": {
                    "event_type": last_incident.event_type.value,
                    "occurred_at": last_incident.occurred_at.isoformat(),
                    "severity": last_incident.severity.value
                } if last_incident else None
            })

        return results

    @staticmethod
    def purge_expired_evidence(
        db: Session,
        retention_days: Optional[int] = None,
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Configurable evidence retention and deletion:
        Wipes sensitive base64 snapshot strings and evidence references older than retention period,
        while preserving incident logs and risk scores for statistical scoring integrity.
        """
        days = retention_days if retention_days is not None else settings.PROCTORING_EVIDENCE_RETENTION_DAYS
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = db.query(ProctoringIncident).filter(
            ProctoringIncident.occurred_at < cutoff,
            (ProctoringIncident.snapshot_data != None) | (ProctoringIncident.evidence_ref != None)
        )

        if assessment_id:
            query = query.join(Attempt).filter(Attempt.assessment_id == assessment_id)

        incidents_to_purge = query.all()
        count = len(incidents_to_purge)

        for inc in incidents_to_purge:
            inc.snapshot_data = None
            inc.evidence_ref = "[PURGED_BY_RETENTION_POLICY]"

        db.commit()
        logger.info(f"Purged {count} expired proctoring snapshots older than {cutoff.isoformat()}")

        return {
            "purged_incidents_count": count,
            "retention_cutoff": cutoff,
            "message": f"Successfully purged evidence for {count} incidents older than {days} days."
        }
