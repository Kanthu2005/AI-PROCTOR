from datetime import datetime, timedelta, timezone
from app.models.candidate import CandidateInvitation, CandidateStatus


def test_bulk_candidate_invitations(client, test_org, recruiter_headers):
    # Create simple assessment
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Invites Test Assessment"
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]

    bulk_payload = {
        "assessment_id": a_id,
        "expires_in_hours": 48,
        "candidates": [
            {"email": "cand1@example.com", "full_name": "Candidate One"},
            {"email": "cand2@example.com", "full_name": "Candidate Two"},
            {"email": "cand3@example.com", "full_name": "Candidate Three"}
        ]
    }
    response = client.post("/api/v1/candidates/bulk-invite", json=bulk_payload, headers=recruiter_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["total_processed"] == 3
    assert len(data["invited_candidates"]) == 3
    for inv in data["invited_candidates"]:
        assert inv["status"] == "INVITED"
        assert len(inv["invitation_token"]) > 20


def test_verify_invitation_token_transitions_to_registered(client, test_org, recruiter_headers):
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Token Verify Assessment"
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]

    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": a_id,
        "candidates": [{"email": "verify_cand@example.com", "full_name": "Verify Candidate"}]
    }, headers=recruiter_headers)
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    verify_res = client.get(f"/api/v1/candidates/invitations/{token}/verify")
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "REGISTERED"


def test_expired_invitation_token_rejected(client, db, test_org, recruiter_headers):
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Expired Token Assessment"
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]

    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": a_id,
        "candidates": [{"email": "expired@example.com", "full_name": "Expired Candidate"}]
    }, headers=recruiter_headers)
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    # Manually backdate expiration time in db
    inv = db.query(CandidateInvitation).filter(CandidateInvitation.invitation_token == token).first()
    inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db.commit()

    verify_res = client.get(f"/api/v1/candidates/invitations/{token}/verify")
    assert verify_res.status_code == 410
    assert "expired" in verify_res.json()["detail"].lower()


def test_system_check_pass_transitions_to_verified(client, test_org, recruiter_headers):
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "System Check Assessment"
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]

    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": a_id,
        "candidates": [{"email": "syscheck@example.com", "full_name": "Sys Check Candidate"}]
    }, headers=recruiter_headers)
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    check_payload = {
        "camera_ok": True,
        "microphone_ok": True,
        "browser_compatible": True,
        "fullscreen_supported": True,
        "face_snapshot_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWP+/HgAEfAI7U+q+0AAAAABJRU5ErkJggg=="
    }
    check_res = client.post(f"/api/v1/candidates/invitations/{token}/system-check", json=check_payload)
    assert check_res.status_code == 200
    assert check_res.json()["status"] == "VERIFIED"
    assert check_res.json()["system_check_passed"] is True


def test_system_check_rejected_when_camera_fails(client, test_org, recruiter_headers):
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Failed Sys Check Assessment"
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]

    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": a_id,
        "candidates": [{"email": "failcam@example.com", "full_name": "Fail Cam"}]
    }, headers=recruiter_headers)
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    check_payload = {
        "camera_ok": False,  # Camera failed
        "microphone_ok": True,
        "browser_compatible": True,
        "fullscreen_supported": True
    }
    check_res = client.post(f"/api/v1/candidates/invitations/{token}/system-check", json=check_payload)
    assert check_res.status_code == 400
    assert "criteria" in check_res.json()["detail"].lower()


def test_disqualified_candidate_cannot_verify(client, db, test_org, recruiter_headers):
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Disqualified Check Assessment"
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]

    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": a_id,
        "candidates": [{"email": "dq@example.com", "full_name": "DQ Candidate"}]
    }, headers=recruiter_headers)
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    inv = db.query(CandidateInvitation).filter(CandidateInvitation.invitation_token == token).first()
    inv.status = CandidateStatus.DISQUALIFIED
    db.commit()

    verify_res = client.get(f"/api/v1/candidates/invitations/{token}/verify")
    assert verify_res.status_code == 403
    assert "disqualified" in verify_res.json()["detail"].lower()
