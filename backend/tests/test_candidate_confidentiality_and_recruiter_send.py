import pytest
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptStatus, AttemptAnswer
from app.utils.security import generate_invitation_token
from datetime import datetime, timezone, timedelta


def test_candidate_submission_receipt_confidentiality_and_recruiter_send(client, test_org, recruiter_headers, db):
    """
    Verifies that:
    1. Candidate submit response NEVER leaks total_score, percentage, or is_passed.
    2. Attempt result query is strictly masked while unreleased.
    3. Recruiter can individually review proctoring checks and send the result.
    4. Released result accurately reflects the recruiter's decision.
    """
    # 1. Create Question via recruiter API
    q_payload = {
        "org_id": test_org.id,
        "title": "Python Data Types",
        "description": "What is type([]) in Python?",
        "question_type": "MCQ_SINGLE",
        "difficulty": "EASY",
        "default_positive_marks": 10.0,
        "default_negative_marks": 0.0,
        "tags": ["python"],
        "options": [
            {"id": "o1", "text": "list", "is_correct": True},
            {"id": "o2", "text": "tuple", "is_correct": False}
        ]
    }
    q_res = client.post("/api/v1/questions", json=q_payload, headers=recruiter_headers)
    assert q_res.status_code == 201
    q_data = q_res.json()
    q_id = q_data["id"]
    qv_id = q_data["current_version"]["id"]

    # 2. Create and Publish Assessment via recruiter API
    a_payload = {
        "org_id": test_org.id,
        "title": "Python Assignment",
        "total_duration_minutes": 60,
        "total_marks": 10.0,
        "passing_percentage": 50.0,
        "sections": [
            {
                "title": "Core Section",
                "order_index": 0,
                "questions": [
                    {
                        "question_id": q_id,
                        "question_version_id": qv_id,
                        "positive_marks": 10.0,
                        "negative_marks": 0.0,
                        "order_index": 0
                    }
                ]
            }
        ]
    }
    a_res = client.post("/api/v1/assessments", json=a_payload, headers=recruiter_headers)
    assert a_res.status_code == 201
    a_id = a_res.json()["id"]

    pub_res = client.post(f"/api/v1/assessments/{a_id}/publish", headers=recruiter_headers)
    assert pub_res.status_code == 200

    sec_id = a_res.json()["sections"][0]["id"]

    # 3. Setup Candidate & Attempt in DB
    inv_token = f"TOKEN_{generate_invitation_token()[:8]}"
    inv = CandidateInvitation(
        assessment_id=a_id,
        org_id=test_org.id,
        email="kanthu@gmail.com",
        full_name="Kanthu",
        invitation_token=inv_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=CandidateStatus.IN_PROGRESS
    )
    db.add(inv)
    db.flush()

    attempt = Attempt(
        invitation_id=inv.id,
        assessment_id=a_id,
        candidate_name="Kanthu",
        candidate_email="kanthu@gmail.com",
        status=AttemptStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
        total_max_marks=10.0
    )
    db.add(attempt)
    db.flush()

    # Add correct answer
    ans = AttemptAnswer(
        attempt_id=attempt.id,
        question_id=q_id,
        question_version_id=qv_id,
        section_id=sec_id,
        selected_option_ids=["o1"]
    )
    db.add(ans)
    db.commit()

    # 4. Candidate Submits Exam
    submit_res = client.post(
        f"/api/v1/attempts/{attempt.id}/submit",
        json={"final_answers": []}
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()

    # CRITICAL CONFIDENTIALITY ASSERTIONS:
    assert sub_data["status"] == "SUBMITTED"
    assert "submission_receipt" in sub_data
    assert sub_data["submission_receipt"].startswith("RCPT-")
    assert sub_data["candidate_name"] == "Kanthu"
    assert sub_data["candidate_email"] == "kanthu@gmail.com"
    # MUST NOT leak scores or pass/fail
    assert "total_score" not in sub_data
    assert "percentage" not in sub_data
    assert "is_passed" not in sub_data
    assert sub_data.get("is_result_released") is False

    # 5. Query Attempt Result Prior to Recruiter Release
    result_res = client.get(f"/api/v1/attempts/{attempt.id}/result")
    assert result_res.status_code == 200
    res_data = result_res.json()
    assert res_data.get("is_result_released") is False
    assert res_data.get("result_decision") == "PENDING_REVIEW"
    assert "total_score" not in res_data
    assert "percentage" not in res_data
    assert "is_passed" not in res_data

    # 6. Recruiter Reviews All Checks and Sends Result
    send_payload = {
        "decision": "PASSED",
        "recruiter_feedback": "All technical and proctoring telemetry checks verified. Passed."
    }
    recruiter_res = client.post(
        f"/api/v1/attempts/{attempt.id}/send-result",
        json=send_payload,
        headers=recruiter_headers
    )
    assert recruiter_res.status_code == 200
    rec_data = recruiter_res.json()
    assert rec_data["is_result_released"] is True
    assert rec_data["result_decision"] == "PASSED"
    assert rec_data["is_passed"] is True
    assert rec_data["total_score"] == 10.0

    # 7. Candidate Query Now Sees Released Decision
    released_res = client.get(f"/api/v1/attempts/{attempt.id}/result")
    assert released_res.status_code == 200
    cand_view = released_res.json()
    assert cand_view.get("is_result_released") is True
    assert cand_view.get("result_decision") == "PASSED"
    assert cand_view.get("is_passed") is True
    assert cand_view.get("total_score") == 10.0
    assert cand_view.get("percentage") == 100.0
    assert cand_view.get("recruiter_feedback") == "All technical and proctoring telemetry checks verified. Passed."
