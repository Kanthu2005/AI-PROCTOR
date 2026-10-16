import uuid
import time
from datetime import datetime, timezone, timedelta
import pytest
from starlette.testclient import TestClient

from app.models.user import Organization, User, Role
from app.models.assessment import Assessment, AssessmentStatus, AssessmentRule
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptStatus, RiskLevel, HumanReviewStatus
from app.models.proctoring import (
    ProctoringIncident, EventType, IncidentSeverity, ProctorReviewDecision, ProctoringEvidenceAccessAudit
)
from app.utils.security import create_access_token
from tests.test_attempt_engine import create_verified_candidate


@pytest.fixture
def proctor_assessment(db, test_org, recruiter):
    assess = Assessment(
        org_id=test_org.id,
        title="Proctoring Comprehensive Assessment",
        status=AssessmentStatus.PUBLISHED,
        total_duration_minutes=60,
        created_by_id=recruiter.id
    )
    db.add(assess)
    db.flush()

    rules = AssessmentRule(
        assessment_id=assess.id,
        max_tab_switches_allowed=3,
        full_screen_enforced=True
    )
    db.add(rules)
    db.commit()
    db.refresh(assess)
    return assess


def test_hardware_permissions_and_connection_events(client, db, test_org, recruiter_headers, author_headers):
    """
    Test camera/mic permission events and connection interruption/restoration telemetries.
    """
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # 1. Device check passed -> 0 points, clean baseline
    dev_res = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "DEVICE_CHECK_PASSED",
        "metadata": {"camera_ready": True, "mic_ready": True}
    })
    assert dev_res.status_code == 200
    assert dev_res.json()["risk_points"] == 0.0
    assert dev_res.json()["current_attempt_risk_score"] == 0.0

    # 2. Connection interrupted -> +10 points
    conn_drop = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "CONNECTION_INTERRUPTED",
        "metadata": {"network_offline": True}
    })
    assert conn_drop.status_code == 200
    assert conn_drop.json()["risk_points"] == 10.0
    assert conn_drop.json()["current_attempt_risk_score"] == 10.0

    # 3. Connection restored -> 0 points, logs re-establishment
    conn_back = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "CONNECTION_RESTORED",
        "metadata": {"network_reconnected": True}
    })
    assert conn_back.status_code == 200
    assert conn_back.json()["risk_points"] == 0.0
    assert conn_back.json()["current_attempt_risk_score"] == 10.0

    # 4. Camera permission revoked during assessment -> +35 points
    cam_denied = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "CAMERA_PERMISSION_DENIED",
        "metadata": {"error": "NotAllowedError: Permission denied"}
    })
    assert cam_denied.status_code == 200
    assert cam_denied.json()["risk_points"] == 35.0
    assert cam_denied.json()["current_attempt_risk_score"] == 45.0
    assert cam_denied.json()["current_risk_level"] == "MEDIUM"


def test_event_spoofing_preventions(client, db, test_org, recruiter_headers, author_headers):
    """
    Test event spoofing guards:
    - Non-existent attempt ID -> 404
    - Completed / submitted attempt -> 400
    - Timestamp in future -> 400
    """
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # 1. Non-existent attempt
    fake_id = str(uuid.uuid4())
    res_fake = client.post(f"/api/v1/proctoring/attempts/{fake_id}/events", json={"event_type": "TAB_SWITCH"})
    assert res_fake.status_code == 404

    # 2. Timestamp far in future (spoofed client clock)
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    res_future = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "TAB_SWITCH",
        "client_timestamp": future_time
    })
    assert res_future.status_code == 400
    assert "future" in res_future.json()["detail"].lower()

    # 3. Completed attempt rejection
    att = db.query(Attempt).filter(Attempt.id == att_id).first()
    att.status = AttemptStatus.SUBMITTED
    db.commit()

    res_completed = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={"event_type": "TAB_SWITCH"})
    assert res_completed.status_code == 400
    assert "completed" in res_completed.json()["detail"].lower()


def test_event_deduplication_burst_prevention(client, db, test_org, recruiter_headers, author_headers):
    """
    Test event deduplication:
    - Same client_event_id is deduplicated and does not duplicate risk points.
    - Rapid burst of identical events with client_timestamp within window is coalesced.
    """
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    client_evt_id = f"evt-{uuid.uuid4().hex}"
    t0 = datetime.now(timezone.utc)

    # 1. First event with client_event_id
    res1 = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "client_event_id": client_evt_id,
        "event_type": "FULLSCREEN_EXIT",
        "client_timestamp": t0.isoformat()
    })
    assert res1.status_code == 200
    assert res1.json()["is_deduplicated"] is False
    assert res1.json()["risk_points"] == 20.0
    assert res1.json()["current_attempt_risk_score"] == 20.0

    # 2. Re-sending identical client_event_id (e.g. network retry) -> Deduplicated!
    res2 = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "client_event_id": client_evt_id,
        "event_type": "FULLSCREEN_EXIT",
        "client_timestamp": t0.isoformat()
    })
    assert res2.status_code == 200
    assert res2.json()["is_deduplicated"] is True
    assert res2.json()["risk_points"] == 0.0
    assert res2.json()["current_attempt_risk_score"] == 20.0  # Did not double-count!

    # 3. Burst coalescing: rapid successive event within 3-second window
    t1 = t0 + timedelta(milliseconds=800)
    res3 = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "FULLSCREEN_EXIT",
        "client_timestamp": t1.isoformat()
    })
    assert res3.status_code == 200
    assert res3.json()["is_deduplicated"] is True
    assert res3.json()["risk_points"] == 0.0
    assert res3.json()["current_attempt_risk_score"] == 20.0


def test_websocket_authorization_and_cross_tenant_isolation(client, db, test_org, proctor, candidate_user, proctor_assessment):
    """
    Test authenticated WebSocket endpoint:
    - Missing token -> 1008 Policy Violation
    - Invalid token -> 1008 Policy Violation
    - Candidate token (insufficient role) -> 1008 Policy Violation
    - Cross-tenant proctor (Org B) attempting Org A -> 1008 Policy Violation
    - Valid proctor of Org A -> Handshake accepted, sends ping/pong
    """
    assess_id = proctor_assessment.id

    # 1. Missing token
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/proctor/{assess_id}") as ws:
            pass

    # 2. Invalid token
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/proctor/{assess_id}?token=invalid-jwt-token") as ws:
            pass

    # 3. Candidate user token (role CANDIDATE lacks proctor privileges)
    cand_token = create_access_token({"sub": candidate_user.id})
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/proctor/{assess_id}?token={cand_token}") as ws:
            pass

    # 4. Cross-tenant proctor: Proctor from Org B
    org_b = Organization(name="Competitor Org B", slug="competitor-org-b")
    db.add(org_b)
    db.flush()
    proctor_b = User(
        email="proctor_b@example.com",
        hashed_password="hashed_pass_placeholder",
        full_name="Proctor B",
        role=Role.PROCTOR,
        org_id=org_b.id,
        is_active=True
    )
    db.add(proctor_b)
    db.commit()
    token_b = create_access_token({"sub": proctor_b.id})

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/proctor/{assess_id}?token={token_b}") as ws:
            pass

    # 5. Valid Proctor of Organization A -> Connection accepted!
    valid_token = create_access_token({"sub": proctor.id})
    with client.websocket_connect(f"/ws/proctor/{assess_id}?token={valid_token}") as ws:
        # Handshake confirmation
        init_msg = ws.receive_json()
        assert init_msg["type"] == "CONNECTION_ESTABLISHED"
        assert init_msg["assessment_id"] == assess_id
        assert init_msg["user_email"] == proctor.email

        # Ping-pong
        ws.send_text("ping")
        pong = ws.receive_text()
        assert pong == "pong"


def test_reviewer_workflow_suspicious_and_escalation(client, db, test_org, recruiter_headers, author_headers, proctor_headers):
    """
    Test reviewer marking an attempt as SUSPICIOUS and escalating to ORG_ADMIN.
    """
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Ingest some suspicious alerts
    client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={"event_type": "DEVTOOLS_OPEN"})

    # Proctor reviews and escalates
    esc_res = client.post(f"/api/v1/proctoring/attempts/{att_id}/review", json={
        "status": "SUSPICIOUS",
        "proctor_notes": "Candidate inspected network tab multiple times.",
        "is_escalated": True,
        "escalated_to_role": "ORG_ADMIN",
        "escalation_reason": "Repeated inspect element opens require senior administrator review"
    }, headers=proctor_headers)

    assert esc_res.status_code == 200
    esc_data = esc_res.json()
    assert esc_data["human_review_status"] == "SUSPICIOUS"
    assert esc_data["is_escalated"] is True
    assert esc_data["escalated_to_role"] == "ORG_ADMIN"

    # Check review history endpoint
    hist_res = client.get(f"/api/v1/proctoring/attempts/{att_id}/review-history", headers=proctor_headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 1
    assert history[0]["decision"] == "SUSPICIOUS"
    assert history[0]["is_escalated"] is True
    assert "inspect element" in history[0]["escalation_reason"]


def test_reviewer_false_positive_handling(client, db, test_org, recruiter_headers, author_headers, proctor_headers):
    """
    Test false positive handling:
    - Automated AI flag flagged candidate (e.g. face missing during sneeze/light glitch).
    - Reviewer inspects evidence and marks as FALSE_POSITIVE.
    - Candidate is NOT disqualified; candidate status remains valid/in-progress.
    - Overriding explanation is logged in risk history.
    """
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Ingest face missing flag
    client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "FACE_MISSING",
        "metadata": {"reason": "Webcam brief occlusion"}
    })

    # Reviewer marks as FALSE_POSITIVE
    fp_res = client.post(f"/api/v1/proctoring/attempts/{att_id}/review", json={
        "status": "FALSE_POSITIVE",
        "proctor_notes": "Candidate sneezed and adjusted chair; face returned immediately. Cleared."
    }, headers=proctor_headers)

    assert fp_res.status_code == 200
    assert fp_res.json()["human_review_status"] == "FALSE_POSITIVE"
    assert fp_res.json()["status"] == "IN_PROGRESS"  # NEVER auto-disqualified!

    # Verify attempt in database
    att = db.query(Attempt).filter(Attempt.id == att_id).first()
    assert att.status == AttemptStatus.IN_PROGRESS
    assert att.human_review_status == HumanReviewStatus.FALSE_POSITIVE

    # Verify explanation logged in risk history
    history = att.risk_history or []
    override_entries = [h for h in history if h.get("event_type") == "HUMAN_REVIEW_OVERRIDE"]
    assert len(override_entries) == 1
    assert "FALSE_POSITIVE" in override_entries[0]["explanation"]


def test_evidence_access_audit_and_polling_fallback(client, db, test_org, recruiter_headers, author_headers, proctor_headers):
    """
    Test evidence access audit logging and polling/reconnect fallback:
    - Viewing candidate incidents logs an audit record in proctoring_evidence_access_audits.
    - Audits can be retrieved via /evidence-access-audit.
    - Polling fallback /live-status provides incremental updates without persistent WebSockets.
    """
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Ingest incident
    client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={
        "event_type": "FULLSCREEN_EXIT",
        "metadata": {"evidence_url": "https://storage.proctorai.internal/evidence/snap_1.jpg"}
    })

    # 1. Proctor views incident evidence
    inc_res = client.get(f"/api/v1/proctoring/attempts/{att_id}/incidents", headers=proctor_headers)
    assert inc_res.status_code == 200
    assert len(inc_res.json()) >= 1

    # 2. Check evidence access audit log
    audit_res = client.get(f"/api/v1/proctoring/attempts/{att_id}/evidence-access-audit", headers=proctor_headers)
    assert audit_res.status_code == 200
    audits = audit_res.json()
    assert len(audits) >= 1
    assert audits[0]["action"] == "EVIDENCE_LIST_VIEW"
    assert audits[0]["user_email"] == "proctor@test.com"

    # 3. Polling fallback endpoint
    poll_res = client.get(f"/api/v1/proctoring/attempts/{att_id}/live-status", headers=proctor_headers)
    assert poll_res.status_code == 200
    poll_data = poll_res.json()
    assert poll_data["attempt_id"] == att_id
    assert poll_data["risk_score"] == 20.0
    assert poll_data["new_incidents_count"] >= 1


def test_privacy_notice_and_evidence_purging(client, db, test_org, recruiter_headers, author_headers, proctor_headers):
    """
    Test privacy transparency notice and configurable evidence purging:
    - GET /privacy-notice returns explainable policy and rights.
    - POST /evidence/purge wipes old base64/snapshot data while keeping risk metrics intact.
    """
    # 1. Privacy notice
    notice_res = client.get("/api/v1/proctoring/privacy-notice")
    assert notice_res.status_code == 200
    notice_data = notice_res.json()
    assert "Privacy Notice" in notice_data["title"]
    assert notice_data["retention_period_days"] == 30
    assert "prioritization signals" in notice_data["ai_use_policy"].lower()

    # 2. Evidence purging
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Create an old incident with snapshot data
    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    old_inc = ProctoringIncident(
        attempt_id=att_id,
        event_type=EventType.FACE_MISSING,
        severity=IncidentSeverity.LOW,
        risk_points=10.0,
        metadata_json={"camera": "webcam_1"},
        snapshot_data="data:image/jpeg;base64,RAW_SENSITIVE_OLD_SNAPSHOT_PAYLOAD_ABC_123",
        evidence_ref="https://storage.proctorai.internal/snap_old.jpg",
        occurred_at=old_time
    )
    db.add(old_inc)
    db.commit()
    db.refresh(old_inc)
    inc_id = old_inc.id

    # Admin purges evidence older than 30 days
    # (recruiter has role RECRUITER; for purge we require ORG_ADMIN or PLATFORM_ADMIN)
    org_admin = User(
        email="org_admin_proctor@test.com",
        hashed_password="hashed_pass_placeholder",
        full_name="Org Admin Proctor",
        role=Role.ORG_ADMIN,
        org_id=test_org.id,
        is_active=True
    )
    db.add(org_admin)
    db.commit()
    admin_token = create_access_token({"sub": org_admin.id})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    purge_res = client.post("/api/v1/proctoring/evidence/purge", json={
        "retention_days": 30
    }, headers=admin_headers)
    assert purge_res.status_code == 200
    assert purge_res.json()["purged_incidents_count"] >= 1

    # Verify incident snapshot was wiped
    refreshed_inc = db.query(ProctoringIncident).filter(ProctoringIncident.id == inc_id).first()
    assert refreshed_inc.snapshot_data is None
    assert refreshed_inc.evidence_ref == "[PURGED_BY_RETENTION_POLICY]"
    # Risk points and occurrence time preserved for scoring integrity!
    assert refreshed_inc.risk_points == 10.0
