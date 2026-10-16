import pytest
from datetime import datetime, timedelta, timezone
from app.models.user import User, Role
from app.models.assessment import Assessment, AssessmentRule, Section, SectionQuestion, AssessmentStatus, NavigationMode
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus


@pytest.fixture
def test_full_assessment(db, test_org, recruiter_headers, author_headers, client):
    # Create Assessment
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Full Candidate Workflow Assessment",
        "description": "Comprehensive engineering evaluation",
        "total_duration_minutes": 45,
        "total_marks": 25.0,
        "passing_percentage": 50.0
    }, headers=recruiter_headers)
    assert assess_res.status_code == 201
    a_id = assess_res.json()["id"]

    # Configure Rules (Randomize + Forward Only testing)
    rule_res = client.put(f"/api/v1/assessments/{a_id}", json={
        "rules": {
            "navigation_mode": "FORWARD_ONLY",
            "randomize_questions": True,
            "randomize_options": True,
            "negative_marking_enabled": True,
            "full_screen_enforced": True,
            "webcam_proctoring_enabled": True
        }
    }, headers=recruiter_headers)
    assert rule_res.status_code == 200

    # Add Section
    sec = Section(assessment_id=a_id, title="Core Engineering", duration_minutes=45, order_index=0)
    db.add(sec)
    db.commit()
    db.refresh(sec)

    # Question 1: MCQ Single
    q1 = Question(org_id=test_org.id, question_type=QuestionType.MCQ_SINGLE)
    db.add(q1)
    db.flush()
    qv1 = QuestionVersion(
        question_id=q1.id, version_number=1, title="Complexity Question", description="Binary search complexity",
        question_type=QuestionType.MCQ_SINGLE, difficulty=DifficultyLevel.EASY,
        options=[
            {"id": "opt_a", "text": "O(log n)", "is_correct": True},
            {"id": "opt_b", "text": "O(n)", "is_correct": False},
            {"id": "opt_c", "text": "O(1)", "is_correct": False}
        ]
    )
    db.add(qv1)
    db.flush()

    # Question 2: Fill in the blank
    q2 = Question(org_id=test_org.id, question_type=QuestionType.FILL_IN_BLANK)
    db.add(q2)
    db.flush()
    qv2 = QuestionVersion(
        question_id=q2.id, version_number=1, title="Python Keyword", description="Keyword to define generator",
        question_type=QuestionType.FILL_IN_BLANK, difficulty=DifficultyLevel.MEDIUM,
        explanation="yield",
        options=[{"text": "yield", "is_correct": True}]
    )
    db.add(qv2)
    db.flush()

    # Question 3: Coding Question
    q3 = Question(org_id=test_org.id, question_type=QuestionType.CODING)
    db.add(q3)
    db.flush()
    qv3 = QuestionVersion(
        question_id=q3.id, version_number=1, title="Sum Array", description="Return sum of array",
        question_type=QuestionType.CODING, difficulty=DifficultyLevel.EASY,
        coding_details={
            "starter_code": "def solve(arr):\n    return sum(arr)\n",
            "language": "python",
            "test_cases": [
                {"input": "1 2 3", "expected_output": "6", "is_hidden": False},
                {"input": "10 20", "expected_output": "30", "is_hidden": True}
            ]
        }
    )
    db.add(qv3)
    db.flush()

    # Link Section Questions
    sq1 = SectionQuestion(section_id=sec.id, question_id=q1.id, question_version_id=qv1.id, positive_marks=5.0, negative_marks=1.0, order_index=0)
    sq2 = SectionQuestion(section_id=sec.id, question_id=q2.id, question_version_id=qv2.id, positive_marks=10.0, negative_marks=2.0, order_index=1)
    sq3 = SectionQuestion(section_id=sec.id, question_id=q3.id, question_version_id=qv3.id, positive_marks=10.0, negative_marks=0.0, order_index=2)
    db.add_all([sq1, sq2, sq3])
    db.commit()

    # Publish Assessment
    pub_res = client.post(f"/api/v1/assessments/{a_id}/publish", headers=recruiter_headers)
    assert pub_res.status_code == 200

    return {
        "assessment_id": a_id,
        "section_id": sec.id,
        "q1": {"id": q1.id, "v_id": qv1.id},
        "q2": {"id": q2.id, "v_id": qv2.id},
        "q3": {"id": q3.id, "v_id": qv3.id}
    }


class TestCandidateAssessmentWorkflow:
    def test_invitation_acceptance_instructions_and_system_check(self, client, test_org, test_full_assessment, recruiter_headers):
        a_id = test_full_assessment["assessment_id"]

        # 1. Invite Candidate
        invite_res = client.post("/api/v1/candidates/bulk-invite", json={
            "assessment_id": a_id,
            "candidates": [{"email": "workflow.candidate@example.com", "full_name": "Workflow Candidate"}],
            "expires_in_hours": 48
        }, headers=recruiter_headers)
        assert invite_res.status_code == 201
        token = invite_res.json()["invited_candidates"][0]["invitation_token"]

        # 2. Candidate loads instructions
        inst_res = client.get(f"/api/v1/candidates/invitations/{token}/instructions")
        assert inst_res.status_code == 200
        inst_data = inst_res.json()
        assert inst_data["assessment_title"] == "Full Candidate Workflow Assessment"
        assert inst_data["duration_minutes"] == 45
        assert inst_data["rules"]["navigation_mode"] == "FORWARD_ONLY"
        assert inst_data["system_check_passed"] is False

        # 3. Hardware Diagnostics / System Check
        check_res = client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
            "camera_ok": True,
            "microphone_ok": True,
            "browser_compatible": True,
            "fullscreen_supported": True,
            "face_snapshot_base64": "data:image/jpeg;base64,mockedfacesnapshot"
        })
        assert check_res.status_code == 200
        assert check_res.json()["status"] == "VERIFIED"
        assert check_res.json()["system_check_passed"] is True

    def test_server_controlled_timer_and_clamped_deadlines(self, client, db, test_org, test_full_assessment, recruiter_headers):
        a_id = test_full_assessment["assessment_id"]

        # Create candidate with verified status
        invite_res = client.post("/api/v1/candidates/bulk-invite", json={
            "assessment_id": a_id,
            "candidates": [{"email": "timer.candidate@example.com", "full_name": "Timer Candidate"}]
        }, headers=recruiter_headers)
        token = invite_res.json()["invited_candidates"][0]["invitation_token"]
        client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
            "camera_ok": True, "microphone_ok": True, "browser_compatible": True, "fullscreen_supported": True
        })

        # Start Attempt
        start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        assert start_res.status_code == 200
        data = start_res.json()
        assert data["status"] == "IN_PROGRESS"
        assert "server_expiry_at" in data
        assert "server_time" in data
        # 45 minutes = 2700s, should be around 2700
        assert 2690 <= data["remaining_seconds"] <= 2700

    def test_reconnect_and_browser_refresh_recovery(self, client, db, test_org, test_full_assessment, recruiter_headers):
        a_id = test_full_assessment["assessment_id"]
        q1_id = test_full_assessment["q1"]["id"]
        qv1_id = test_full_assessment["q1"]["v_id"]
        sec_id = test_full_assessment["section_id"]

        invite_res = client.post("/api/v1/candidates/bulk-invite", json={
            "assessment_id": a_id,
            "candidates": [{"email": "reconnect.candidate@example.com", "full_name": "Reconnect Candidate"}]
        }, headers=recruiter_headers)
        token = invite_res.json()["invited_candidates"][0]["invitation_token"]
        client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
            "camera_ok": True, "microphone_ok": True, "browser_compatible": True, "fullscreen_supported": True
        })

        # Launch attempt
        start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        att_id = start_res.json()["attempt_id"]

        # Autosave an answer with review flag
        save_res = client.post(f"/api/v1/attempts/{att_id}/answers/autosave", json={
            "answers": [
                {
                    "question_id": q1_id,
                    "question_version_id": qv1_id,
                    "section_id": sec_id,
                    "selected_option_ids": ["opt_a"],
                    "time_spent_seconds": 45,
                    "is_flagged_for_review": True
                }
            ],
            "current_question_id": q1_id
        })
        assert save_res.status_code == 200
        assert save_res.json()["success"] is True
        assert q1_id in save_res.json()["saved_question_ids"]

        # Simulate browser refresh by calling state endpoint
        state_res = client.get(f"/api/v1/attempts/{att_id}/state")
        assert state_res.status_code == 200
        state_data = state_res.json()
        assert state_data["status"] == "IN_PROGRESS"
        assert state_data["current_question_id"] == q1_id
        assert q1_id in state_data["saved_answers"]
        saved_q1 = state_data["saved_answers"][q1_id]
        assert saved_q1["selected_option_ids"] == ["opt_a"]
        assert saved_q1["is_flagged_for_review"] is True
        assert saved_q1["time_spent_seconds"] == 45

        # Also verify that start_attempt with same token recovers the exact same state
        re_start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        assert re_start_res.status_code == 200
        re_data = re_start_res.json()
        assert re_data["attempt_id"] == att_id
        assert q1_id in re_data["saved_answers"]

    def test_deterministic_question_randomization_on_refresh(self, client, test_org, test_full_assessment, recruiter_headers):
        a_id = test_full_assessment["assessment_id"]

        invite_res = client.post("/api/v1/candidates/bulk-invite", json={
            "assessment_id": a_id,
            "candidates": [{"email": "shuffle.candidate@example.com", "full_name": "Shuffle Candidate"}]
        }, headers=recruiter_headers)
        token = invite_res.json()["invited_candidates"][0]["invitation_token"]
        client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
            "camera_ok": True, "microphone_ok": True, "browser_compatible": True, "fullscreen_supported": True
        })

        # First load
        res1 = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        assert res1.status_code == 200
        q_order_1 = [q["question_id"] for q in res1.json()["sections"][0]["questions"]]
        opts_order_1 = [o["id"] for o in res1.json()["sections"][0]["questions"][0]["options"]]

        # Second load (simulate browser reload)
        res2 = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        assert res2.status_code == 200
        q_order_2 = [q["question_id"] for q in res2.json()["sections"][0]["questions"]]
        opts_order_2 = [o["id"] for o in res2.json()["sections"][0]["questions"][0]["options"]]

        # Deterministic order preserved across reloads!
        assert q_order_1 == q_order_2
        assert opts_order_1 == opts_order_2

    def test_manual_submission_and_receipt_generation(self, client, test_org, test_full_assessment, recruiter_headers):
        a_id = test_full_assessment["assessment_id"]
        q1_id = test_full_assessment["q1"]["id"]
        qv1_id = test_full_assessment["q1"]["v_id"]
        q2_id = test_full_assessment["q2"]["id"]
        qv2_id = test_full_assessment["q2"]["v_id"]
        sec_id = test_full_assessment["section_id"]

        invite_res = client.post("/api/v1/candidates/bulk-invite", json={
            "assessment_id": a_id,
            "candidates": [{"email": "manual.submit@example.com", "full_name": "Manual Submitter"}]
        }, headers=recruiter_headers)
        token = invite_res.json()["invited_candidates"][0]["invitation_token"]
        client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
            "camera_ok": True, "microphone_ok": True, "browser_compatible": True, "fullscreen_supported": True
        })

        start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        att_id = start_res.json()["attempt_id"]

        # Submit with correct answers for Q1 (5 marks) and Q2 (10 marks) -> 15/25 = 60% (Passing >= 50%)
        submit_res = client.post(f"/api/v1/attempts/{att_id}/submit", json={
            "final_answers": [
                {
                    "question_id": q1_id,
                    "question_version_id": qv1_id,
                    "section_id": sec_id,
                    "selected_option_ids": ["opt_a"]
                },
                {
                    "question_id": q2_id,
                    "question_version_id": qv2_id,
                    "section_id": sec_id,
                    "text_response": "yield"
                }
            ]
        })
        assert submit_res.status_code == 200
        sub_data = submit_res.json()
        assert sub_data["status"] == "SUBMITTED"
        assert sub_data["submission_type"] == "MANUAL"
        assert sub_data["submission_receipt"].startswith("RCPT-")
        assert sub_data["total_score"] == 15.0
        assert sub_data["percentage"] == 60.0
        assert sub_data["is_passed"] is True
        assert sub_data["answered_count"] == 2
        assert sub_data["total_questions"] == 3

    def test_idempotent_submission_and_duplicate_safety(self, client, test_org, test_full_assessment, recruiter_headers):
        a_id = test_full_assessment["assessment_id"]
        invite_res = client.post("/api/v1/candidates/bulk-invite", json={
            "assessment_id": a_id,
            "candidates": [{"email": "duplicate.sub@example.com", "full_name": "Duplicate Submitter"}]
        }, headers=recruiter_headers)
        token = invite_res.json()["invited_candidates"][0]["invitation_token"]
        client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
            "camera_ok": True, "microphone_ok": True, "browser_compatible": True, "fullscreen_supported": True
        })

        start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        att_id = start_res.json()["attempt_id"]

        # First Submission
        sub1 = client.post(f"/api/v1/attempts/{att_id}/submit", json={"final_answers": []})
        assert sub1.status_code == 200
        receipt1 = sub1.json()["submission_receipt"]

        # Duplicate submission should be idempotent, returning the same receipt without error
        sub2 = client.post(f"/api/v1/attempts/{att_id}/submit", json={"final_answers": []})
        assert sub2.status_code == 200
        receipt2 = sub2.json()["submission_receipt"]
        assert receipt1 == receipt2

        # Autosave after submission MUST be rejected
        save_after = client.post(f"/api/v1/attempts/{att_id}/answers/autosave", json={"answers": []})
        assert save_after.status_code == 400
        assert "cannot save answers" in save_after.json()["detail"].lower()

    def test_deadline_based_automatic_submission(self, client, db, test_org, test_full_assessment, recruiter_headers):
        a_id = test_full_assessment["assessment_id"]
        q1_id = test_full_assessment["q1"]["id"]
        qv1_id = test_full_assessment["q1"]["v_id"]
        sec_id = test_full_assessment["section_id"]

        invite_res = client.post("/api/v1/candidates/bulk-invite", json={
            "assessment_id": a_id,
            "candidates": [{"email": "autosubmit.candidate@example.com", "full_name": "AutoSubmit Candidate"}]
        }, headers=recruiter_headers)
        token = invite_res.json()["invited_candidates"][0]["invitation_token"]
        client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
            "camera_ok": True, "microphone_ok": True, "browser_compatible": True, "fullscreen_supported": True
        })

        start_res = client.post(f"/api/v1/attempts/start?invitation_token={token}")
        att_id = start_res.json()["attempt_id"]

        # Manually expire server_expiry_at on the attempt to simulate timer running out
        att = db.query(Attempt).filter(Attempt.id == att_id).first()
        att.server_expiry_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()

        # Autosave call detects expiration and triggers automatic auto-submission
        auto_res = client.post(f"/api/v1/attempts/{att_id}/answers/autosave", json={
            "answers": [
                {
                    "question_id": q1_id,
                    "question_version_id": qv1_id,
                    "section_id": sec_id,
                    "selected_option_ids": ["opt_a"]
                }
            ]
        })
        assert auto_res.status_code == 200
        data = auto_res.json()
        assert data["is_auto_submitted"] is True
        assert data["remaining_seconds"] == 0
        assert data["submission_receipt"].startswith("RCPT-")

        # Verify DB attempt state
        db.refresh(att)
        assert att.status == AttemptStatus.AUTO_SUBMITTED
        assert att.submission_type == "AUTO_DEADLINE"
        assert att.total_score == 5.0
