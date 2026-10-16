import pytest
from app.models.attempt import Attempt, AttemptStatus, RiskLevel, HumanReviewStatus
from app.models.candidate import CandidateStatus
from app.services.proctoring_service import ProctoringService
from tests.test_attempt_engine import create_verified_candidate


def test_tab_switch_increments_risk_and_counter(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    event_payload = {
        "event_type": "TAB_SWITCH",
        "metadata": {"window_blurred": True}
    }
    res = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json=event_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_points"] == 15.0
    assert data["current_attempt_risk_score"] == 15.0
    assert data["current_risk_level"] == "LOW"

    # Check attempt in DB
    att = db.query(Attempt).filter(Attempt.id == att_id).first()
    assert att.tab_switch_count == 1


def test_devtools_open_triggers_high_risk(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    event_payload = {
        "event_type": "DEVTOOLS_OPEN",
        "metadata": {"key_pressed": "F12"}
    }
    res = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json=event_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_points"] == 40.0
    assert data["current_attempt_risk_score"] == 40.0
    assert data["current_risk_level"] == "MEDIUM"


def test_dynamic_risk_level_accumulation_to_critical(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # 1. DevTools (+40 -> 40, MEDIUM)
    client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={"event_type": "DEVTOOLS_OPEN"})
    # 2. Fullscreen Exit (+20 -> 60, HIGH)
    res2 = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={"event_type": "FULLSCREEN_EXIT"})
    assert res2.json()["current_risk_level"] == "HIGH"

    # 3. Another DevTools (+40 -> 100, CRITICAL)
    res3 = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={"event_type": "DEVTOOLS_OPEN"})
    assert res3.json()["current_risk_level"] == "CRITICAL"
    assert res3.json()["current_attempt_risk_score"] == 100.0


def test_exceeding_tab_switches_auto_disqualifies_candidate(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Assessment allows 3 tab switches. 4th should disqualify!
    for i in range(3):
        res = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={"event_type": "TAB_SWITCH"})
        assert res.json()["disqualified"] is False

    # 4th switch
    res4 = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json={"event_type": "TAB_SWITCH"})
    assert res4.json()["disqualified"] is True
    assert "exceeded" in res4.json()["disqualification_reason"].lower()

    # Verify attempt and invitation status in DB
    att = db.query(Attempt).filter(Attempt.id == att_id).first()
    assert att.status == AttemptStatus.DISQUALIFIED
    assert att.invitation.status == CandidateStatus.DISQUALIFIED


def test_cv_proctor_analysis_multiple_faces(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Simulated snapshot base64 containing MULTIPLE_FACES
    import base64
    fake_img = base64.b64encode(b"SIMULATE_MULTIPLE_FACES_TEST_IMAGE_PAYLOAD_XYZ_1234567890").decode("utf-8")
    event_payload = {
        "event_type": "FACE_MISSING",
        "snapshot_base64": f"data:image/jpeg;base64,{fake_img}"
    }
    res = client.post(f"/api/v1/proctoring/attempts/{att_id}/events", json=event_payload)
    assert res.status_code == 200
    assert res.json()["event_type"] == "MULTIPLE_FACES"
    assert res.json()["risk_points"] == 30.0


def test_human_proctor_review_workflow(client, db, test_org, recruiter_headers, author_headers, proctor_headers):
    token, a_id, _, _, _ = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Proctor reviews and marks as VALID
    review_res = client.post(f"/api/v1/proctoring/attempts/{att_id}/review", json={
        "status": "VALID",
        "proctor_notes": "Looked clean on webcam playback."
    }, headers=proctor_headers)
    assert review_res.status_code == 200
    assert review_res.json()["human_review_status"] == "VALID"

    # Proctor changes verdict to CONFIRMED_VIOLATION
    violation_res = client.post(f"/api/v1/proctoring/attempts/{att_id}/review", json={
        "status": "CONFIRMED_VIOLATION",
        "proctor_notes": "Second person sitting next to candidate feeding answers."
    }, headers=proctor_headers)
    assert violation_res.status_code == 200
    assert violation_res.json()["status"] == "DISQUALIFIED"
    assert "Second person" in violation_res.json()["disqualified_reason"]
