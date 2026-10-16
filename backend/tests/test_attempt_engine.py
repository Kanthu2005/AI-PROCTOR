from datetime import datetime, timedelta, timezone
from app.models.attempt import Attempt, AttemptStatus
from app.models.candidate import CandidateInvitation, CandidateStatus


def create_verified_candidate(client, db, test_org, recruiter_headers, author_headers):
    # 1. Create Question
    q_res = client.post("/api/v1/questions", json={
        "org_id": test_org.id,
        "title": "Engine Test Q",
        "description": "What is 10 * 10?",
        "question_type": "MCQ_SINGLE",
        "default_positive_marks": 5.0,
        "default_negative_marks": 1.0,
        "options": [
            {"id": "opt_100", "text": "100", "is_correct": True},
            {"id": "opt_10", "text": "10", "is_correct": False}
        ]
    }, headers=author_headers)
    q_id = q_res.json()["id"]
    qv_id = q_res.json()["current_version"]["id"]

    # 2. Create Assessment
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Attempt Engine Assessment",
        "total_duration_minutes": 30,
        "passing_percentage": 50.0,
        "sections": [{
            "title": "Section 1",
            "questions": [{"question_id": q_id, "positive_marks": 5.0, "negative_marks": 1.0}]
        }]
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]
    s_id = assess_res.json()["sections"][0]["id"]

    # 3. Invite Candidate
    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": a_id,
        "candidates": [{"email": "testengine@example.com", "full_name": "Test Engine Candidate"}]
    }, headers=recruiter_headers)
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    # 4. Perform System Check
    client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
        "camera_ok": True,
        "microphone_ok": True,
        "browser_compatible": True,
        "fullscreen_supported": True
    })

    return token, a_id, s_id, q_id, qv_id


def test_start_attempt_initializes_server_timer(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, s_id, q_id, qv_id = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)

    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    assert start_res.status_code == 200
    data = start_res.json()
    assert "attempt_id" in data
    assert data["status"] == "IN_PROGRESS"
    assert "server_expiry_at" in data
    assert data["remaining_seconds"] > 1700  # 30 mins approx 1800s


def test_start_attempt_rejected_without_system_check(client, test_org, recruiter_headers):
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "No Check Assessment"
    }, headers=recruiter_headers)
    a_id = assess_res.json()["id"]

    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": a_id,
        "candidates": [{"email": "nocheck@example.com", "full_name": "No Check"}]
    }, headers=recruiter_headers)
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    assert start_res.status_code == 400
    assert "system compatibility" in start_res.json()["detail"].lower()


def test_background_autosave_success(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, s_id, q_id, qv_id = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    save_payload = {
        "answers": [
            {
                "question_id": q_id,
                "question_version_id": qv_id,
                "section_id": s_id,
                "selected_option_ids": ["opt_100"],
                "time_spent_seconds": 15
            }
        ]
    }
    save_res = client.post(f"/api/v1/attempts/{att_id}/answers/autosave", json=save_payload)
    assert save_res.status_code == 200
    save_data = save_res.json()
    assert save_data["success"] is True
    assert save_data["saved_count"] == 1
    assert save_data["is_auto_submitted"] is False
    assert save_data["remaining_seconds"] > 0


def test_autosave_triggers_auto_submit_when_timer_expires(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, s_id, q_id, qv_id = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Manually backdate server_expiry_at on the attempt to simulate timer expiration
    att = db.query(Attempt).filter(Attempt.id == att_id).first()
    att.server_expiry_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db.commit()

    save_payload = {
        "answers": [
            {
                "question_id": q_id,
                "question_version_id": qv_id,
                "section_id": s_id,
                "selected_option_ids": ["opt_100"],
                "time_spent_seconds": 30
            }
        ]
    }
    save_res = client.post(f"/api/v1/attempts/{att_id}/answers/autosave", json=save_payload)
    assert save_res.status_code == 200
    save_data = save_res.json()
    assert save_data["is_auto_submitted"] is True
    assert save_data["remaining_seconds"] == 0

    # Verify attempt in DB is now AUTO_SUBMITTED with evaluation score
    db.refresh(att)
    assert att.status == AttemptStatus.AUTO_SUBMITTED
    assert att.total_score == 5.0
    assert att.is_passed is True


def test_manual_submission_evaluates_scores(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, s_id, q_id, qv_id = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    submit_payload = {
        "final_answers": [
            {
                "question_id": q_id,
                "question_version_id": qv_id,
                "section_id": s_id,
                "selected_option_ids": ["opt_100"],  # Correct option!
                "time_spent_seconds": 25
            }
        ]
    }
    sub_res = client.post(f"/api/v1/attempts/{att_id}/submit", json=submit_payload)
    assert sub_res.status_code == 200
    data = sub_res.json()
    assert data["status"] == "SUBMITTED"
    assert data["total_score"] == 5.0
    assert data["percentage"] == 100.0
    assert data["is_passed"] is True


def test_submission_with_incorrect_answer_applies_negative_marking(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, s_id, q_id, qv_id = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    submit_payload = {
        "final_answers": [
            {
                "question_id": q_id,
                "question_version_id": qv_id,
                "section_id": s_id,
                "selected_option_ids": ["opt_10"],  # Wrong option (penalty = 1.0)
                "time_spent_seconds": 15
            }
        ]
    }
    sub_res = client.post(f"/api/v1/attempts/{att_id}/submit", json=submit_payload)
    assert sub_res.status_code == 200
    data = sub_res.json()
    # Total score bounded at 0.0
    assert data["total_score"] == 0.0
    assert data["is_passed"] is False


def test_cannot_save_after_submission(client, db, test_org, recruiter_headers, author_headers):
    token, a_id, s_id, q_id, qv_id = create_verified_candidate(client, db, test_org, recruiter_headers, author_headers)
    start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    att_id = start_res.json()["attempt_id"]

    # Submit
    client.post(f"/api/v1/attempts/{att_id}/submit", json={"final_answers": []})

    # Attempt to autosave again
    save_res = client.post(f"/api/v1/attempts/{att_id}/answers/autosave", json={"answers": []})
    assert save_res.status_code == 400
    assert "cannot save answers" in save_res.json()["detail"].lower()
