import pytest
from datetime import datetime, timedelta, timezone
from app.models.assessment import AssessmentStatus
from app.models.question import QuestionType, ReviewStatus
from app.models.user import Organization


@pytest.fixture
def other_org(db):
    org = Organization(name="Other Organization", slug="otherorg", domain="other.com", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def other_recruiter(db, other_org):
    from app.models.user import User, Role
    from app.utils.security import hash_password, create_access_token
    user = User(
        email="other_recruiter@other.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Other Recruiter",
        role=Role.RECRUITER,
        org_id=other_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_recruiter_headers(other_recruiter):
    from app.utils.security import create_access_token
    token = create_access_token({
        "sub": other_recruiter.id,
        "role": other_recruiter.role.value,
        "org_id": other_recruiter.org_id
    })
    return {"Authorization": f"Bearer {token}"}


class TestRecruiterWorkflowPhase2:
    """
    Acceptance test suite for Phase 2: Recruiter Workflow
    Covers:
    - Assessment lifecycle state machine (DRAFT -> PUBLISHED -> SCHEDULED -> CLOSED)
    - Rejection of invalid transitions (e.g. publishing empty assessment, editing closed assessment)
    - Assessment duplication with frozen question versions
    - Question approval & review states (DRAFT -> APPROVED)
    - Multi-type questions (TRUE_FALSE, FILL_IN_BLANK, SHORT_ANSWER)
    - Question duplication and soft deletion
    - Candidate invitation lifecycle (single invite, bulk invite, token revocation, resend)
    - Tenant isolation (IDOR protection on assessments, questions, invitations)
    - RBAC permissions (unauthorized role rejections)
    """

    def test_question_creation_and_approval_workflow(self, client, test_org, recruiter_headers):
        # 1. Create a True/False question
        tf_payload = {
            "org_id": test_org.id,
            "title": "Python lists are mutable.",
            "description": "Fundamental python sequence type question",
            "question_type": "TRUE_FALSE",
            "difficulty": "EASY",
            "default_positive_marks": 2.0,
            "default_negative_marks": 0.5,
            "tags": ["python", "data-structures"],
            "options": [
                {"id": "opt_true", "text": "True", "is_correct": True},
                {"id": "opt_false", "text": "False", "is_correct": False}
            ]
        }
        res = client.post("/api/v1/questions", json=tf_payload, headers=recruiter_headers)
        assert res.status_code == 201
        data = res.json()
        q_id = data["id"]
        assert data["question_type"] == "TRUE_FALSE"
        assert data["current_version"]["review_status"] == "DRAFT"

        # 2. Review and Approve the question
        review_res = client.post(f"/api/v1/questions/{q_id}/review", json={"review_status": "APPROVED"}, headers=recruiter_headers)
        assert review_res.status_code == 200
        review_data = review_res.json()
        assert review_data.get("review_status") == "APPROVED" or review_data.get("current_version", {}).get("review_status") == "APPROVED"

        # 3. Duplicate the question
        dup_res = client.post(f"/api/v1/questions/{q_id}/duplicate", headers=recruiter_headers)
        assert dup_res.status_code == 201
        dup_data = dup_res.json()
        assert dup_data["id"] != q_id
        assert "(Copy)" in dup_data["current_version"]["title"] or "Copy of" in dup_data["current_version"]["title"]
        assert dup_data["current_version"]["review_status"] == "DRAFT"

        # 4. Soft delete the duplicated question
        del_res = client.delete(f"/api/v1/questions/{dup_data['id']}", headers=recruiter_headers)
        assert del_res.status_code == 200

        # Query list should no longer return soft-deleted question
        list_res = client.get(f"/api/v1/questions?org_id={test_org.id}", headers=recruiter_headers)
        ids = [item["id"] for item in list_res.json()]
        assert dup_data["id"] not in ids

    def test_assessment_creation_and_lifecycle(self, client, test_org, recruiter_headers):
        # 1. Create a draft question first
        q_payload = {
            "org_id": test_org.id,
            "title": "Explain REST vs GraphQL",
            "description": "API architectural paradigms",
            "question_type": "SHORT_ANSWER",
            "difficulty": "MEDIUM",
            "default_positive_marks": 5.0,
            "tags": ["web", "architecture"]
        }
        q_res = client.post("/api/v1/questions", json=q_payload, headers=recruiter_headers)
        assert q_res.status_code == 201
        question_id = q_res.json()["id"]

        # 2. Create an Assessment in DRAFT status
        assess_payload = {
            "org_id": test_org.id,
            "title": "Full Stack Senior Engineer Evaluation",
            "description": "Comprehensive engineering evaluation",
            "instructions": "All tests must be performed under proctored supervision",
            "total_duration_minutes": 90,
            "total_marks": 100.0,
            "passing_percentage": 60.0,
            "rules": {
                "navigation_mode": "FREE",
                "randomize_questions": True,
                "negative_marking_enabled": True
            },
            "sections": [
                {
                    "title": "System Design & Architecture",
                    "duration_minutes": 45,
                    "order_index": 1,
                    "cut_off_marks": 20.0,
                    "questions": [
                        {
                            "question_id": question_id,
                            "positive_marks": 5.0,
                            "negative_marks": 0.0,
                            "order_index": 1
                        }
                    ]
                }
            ]
        }
        create_res = client.post("/api/v1/assessments", json=assess_payload, headers=recruiter_headers)
        assert create_res.status_code == 201
        assess_data = create_res.json()
        assess_id = assess_data["id"]
        assert assess_data["status"] == "DRAFT"
        assert len(assess_data["sections"]) == 1
        assert len(assess_data["sections"][0]["section_questions"]) == 1
        # Question version must be frozen and assigned
        assert assess_data["sections"][0]["section_questions"][0]["question_version_id"] is not None

        # 3. Publish the assessment
        pub_res = client.post(f"/api/v1/assessments/{assess_id}/publish", headers=recruiter_headers)
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "PUBLISHED"

        # 4. Schedule the assessment
        start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        sched_res = client.post(
            f"/api/v1/assessments/{assess_id}/schedule",
            json={"start_time": start, "end_time": end},
            headers=recruiter_headers
        )
        assert sched_res.status_code == 200
        assert sched_res.json()["status"] == "SCHEDULED"

        # 5. Duplicate the assessment
        dup_res = client.post(f"/api/v1/assessments/{assess_id}/duplicate", headers=recruiter_headers)
        assert dup_res.status_code == 201
        dup_assess = dup_res.json()
        assert dup_assess["id"] != assess_id
        assert "(Copy)" in dup_assess["title"] or "Copy of" in dup_assess["title"]
        assert dup_assess["status"] == "DRAFT"
        assert len(dup_assess["sections"]) == 1
        assert len(dup_assess["sections"][0]["section_questions"]) == 1

        # 6. Close the original assessment
        close_res = client.post(f"/api/v1/assessments/{assess_id}/close", headers=recruiter_headers)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "CLOSED"

        # 7. Updating a closed assessment should be rejected
        edit_closed_res = client.put(
            f"/api/v1/assessments/{assess_id}",
            json={"title": "Modified Title"},
            headers=recruiter_headers
        )
        assert edit_closed_res.status_code == 400
        assert "CLOSED status" in edit_closed_res.json()["detail"]

    def test_cannot_publish_empty_assessment(self, client, test_org, recruiter_headers):
        # Create an assessment with no sections/questions
        assess_payload = {
            "org_id": test_org.id,
            "title": "Empty Assessment",
            "total_duration_minutes": 30,
            "sections": []
        }
        res = client.post("/api/v1/assessments", json=assess_payload, headers=recruiter_headers)
        assert res.status_code == 201
        empty_id = res.json()["id"]

        # Attempt to publish should fail with 400
        pub_res = client.post(f"/api/v1/assessments/{empty_id}/publish", headers=recruiter_headers)
        assert pub_res.status_code == 400
        assert "zero questions" in pub_res.json()["detail"]

    def test_candidate_invitation_lifecycle_and_actions(self, client, test_org, recruiter_headers):
        # Create valid assessment with 1 question
        q_res = client.post("/api/v1/questions", json={
            "org_id": test_org.id,
            "title": "Fill in the blank: HTTP 404 means _____",
            "question_type": "FILL_IN_BLANK",
            "difficulty": "EASY",
            "default_positive_marks": 1.0,
            "tags": ["http"]
        }, headers=recruiter_headers)
        q_id = q_res.json()["id"]

        a_res = client.post("/api/v1/assessments", json={
            "org_id": test_org.id,
            "title": "Candidate Screening Exam",
            "sections": [{
                "title": "Section A",
                "questions": [{"question_id": q_id, "positive_marks": 1.0}]
            }]
        }, headers=recruiter_headers)
        assessment_id = a_res.json()["id"]

        # 1. Single candidate invite via POST /api/v1/candidates/invite
        single_res = client.post("/api/v1/candidates/invite", json={
            "assessment_id": assessment_id,
            "email": "candidate.single@example.com",
            "full_name": "Alice Single",
            "expires_in_hours": 48
        }, headers=recruiter_headers)
        assert single_res.status_code == 200
        inv_data = single_res.json()
        inv_id = inv_data["id"]
        token_orig = inv_data["invitation_token"]
        assert inv_data["status"] == "INVITED"

        # 2. Resend invitation (regenerates token and resets expiration)
        resend_res = client.post(f"/api/v1/candidates/invitations/{inv_id}/resend", headers=recruiter_headers)
        assert resend_res.status_code == 200
        refreshed_data = resend_res.json()
        assert refreshed_data["invitation_token"] != token_orig
        assert refreshed_data["status"] == "INVITED"

        # 3. Revoke invitation
        revoke_res = client.delete(f"/api/v1/candidates/invitations/{inv_id}", headers=recruiter_headers)
        assert revoke_res.status_code == 200

        # Attempting to verify the revoked token should now return 404
        verify_res = client.get(f"/api/v1/candidates/invitations/{refreshed_data['invitation_token']}/verify")
        assert verify_res.status_code == 404

    def test_tenant_isolation_cross_org_access_forbidden(
        self, client, test_org, other_org, recruiter_headers, other_recruiter_headers
    ):
        # Create assessment in test_org
        q_res = client.post("/api/v1/questions", json={
            "org_id": test_org.id,
            "title": "Confidential internal algorithm question",
            "question_type": "SHORT_ANSWER"
        }, headers=recruiter_headers)
        q_id = q_res.json()["id"]

        a_res = client.post("/api/v1/assessments", json={
            "org_id": test_org.id,
            "title": "Internal Company Assessment",
            "sections": [{
                "title": "Internal Section",
                "questions": [{"question_id": q_id, "positive_marks": 1.0}]
            }]
        }, headers=recruiter_headers)
        assess_id = a_res.json()["id"]

        # Recruiter from other_org must be forbidden (HTTP 403) from accessing test_org's assessment
        get_res = client.get(f"/api/v1/assessments/{assess_id}", headers=other_recruiter_headers)
        assert get_res.status_code == 403
        assert "Cannot access assessments belonging to another organization" in get_res.json()["detail"]

        # Recruiter from other_org must be forbidden from publishing test_org's assessment
        pub_res = client.post(f"/api/v1/assessments/{assess_id}/publish", headers=other_recruiter_headers)
        assert pub_res.status_code == 403

        # Recruiter from other_org must be forbidden from inviting candidates to test_org's assessment
        inv_res = client.post("/api/v1/candidates/invite", json={
            "assessment_id": assess_id,
            "email": "hacker@other.com",
            "full_name": "Intruder"
        }, headers=other_recruiter_headers)
        assert inv_res.status_code == 403

    def test_rbac_unauthorized_role_restrictions(self, client, test_org, candidate_headers, recruiter_headers):
        # Candidate role cannot create questions
        q_res = client.post("/api/v1/questions", json={
            "org_id": test_org.id,
            "title": "Candidate trying to create question",
            "question_type": "MCQ_SINGLE"
        }, headers=candidate_headers)
        assert q_res.status_code == 403

        # Candidate role cannot create assessments
        a_res = client.post("/api/v1/assessments", json={
            "org_id": test_org.id,
            "title": "Candidate trying to create assessment"
        }, headers=candidate_headers)
        assert a_res.status_code == 403

        # Candidate role cannot invite other candidates
        inv_res = client.post("/api/v1/candidates/invite", json={
            "assessment_id": "assess_123",
            "email": "friend@test.com",
            "full_name": "Friend"
        }, headers=candidate_headers)
        assert inv_res.status_code == 403
