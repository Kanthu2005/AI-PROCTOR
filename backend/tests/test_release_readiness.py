import pytest
import time
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.models.user import User, Role, Organization, SecurityAuditEvent
from app.models.assessment import Assessment, AssessmentRule, Section, SectionQuestion, AssessmentStatus
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus
from app.services.auth_service import AuthRateLimiter
from app.utils.security import hash_password, is_demo_replayable_token


class TestReleaseReadiness:
    """
    Release-Readiness Test Suite verifying security controls, RBAC, IDOR protection,
    token integrity, rate limiting, and failure handling.
    """

    def test_auth_rate_limiting_brute_force_protection(self, client, db, test_org):
        """
        Tests sliding-window rate limiting on login attempts.
        Exceeding AUTH_RATE_LIMIT_PER_MINUTE must return HTTP 429 with Retry-After header.
        """
        AuthRateLimiter.reset()
        test_email = "brute_force_target@example.com"

        # Make failed attempts up to the limit
        limit = settings.AUTH_RATE_LIMIT_PER_MINUTE
        for i in range(limit):
            res = client.post("/api/v1/auth/login", json={
                "email": test_email,
                "password": f"WrongPass@{i}"
            })
            assert res.status_code == 401

        # The (limit + 1)-th attempt must be rejected with 429 Too Many Requests
        rate_limited_res = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "AnyPassword@123"
        })
        assert rate_limited_res.status_code == 429
        assert "Too many login attempts" in rate_limited_res.json()["detail"]
        assert "Retry-After" in rate_limited_res.headers

        # Verify rate-limit audit event was persisted
        audit_event = db.query(SecurityAuditEvent).filter(
            SecurityAuditEvent.event_type == "LOGIN_RATE_LIMITED",
            SecurityAuditEvent.email == test_email
        ).first()
        assert audit_event is not None

        # Clean up rate limiter
        AuthRateLimiter.reset()

    def test_expired_invitation_token_rejected(self, client, db, test_org, recruiter_headers):
        """
        Tests that candidate invitation links past expires_at return HTTP 410 Gone.
        """
        # Create published assessment
        assess = Assessment(
            org_id=test_org.id,
            title="Expiry Test Assessment",
            status=AssessmentStatus.PUBLISHED,
            total_duration_minutes=30
        )
        db.add(assess)
        db.commit()
        db.refresh(assess)

        # Create expired invitation
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        inv = CandidateInvitation(
            assessment_id=assess.id,
            org_id=test_org.id,
            email="expired.candidate@example.com",
            full_name="Expired Candidate",
            invitation_token="EXPIRED_TOKEN_SECURE_123",
            expires_at=past_time,
            status=CandidateStatus.INVITED
        )
        db.add(inv)
        db.commit()

        # Instructions endpoint must return 410 Gone
        inst_res = client.get(f"/api/v1/candidates/invitations/{inv.invitation_token}/instructions")
        assert inst_res.status_code == 410
        assert "expired" in inst_res.json()["detail"].lower()

        # Starting attempt must return 410 Gone
        start_res = client.post(f"/api/v1/attempts/start?invitation_token={inv.invitation_token}")
        assert start_res.status_code == 410
        assert "expired" in start_res.json()["detail"].lower()

    def test_token_replay_rejected_after_submission(self, client, db, test_org, recruiter_headers):
        """
        Tests that submitted assessment tokens cannot be replayed or restarted.
        Verifies that tokens starting with 'ABC' do NOT trigger demo bypass in test/production.
        """
        # Assert is_demo_replayable_token is False in test environment
        assert is_demo_replayable_token("ABC123_RANDOM_TOKEN") is False

        assess = Assessment(
            org_id=test_org.id,
            title="Replay Test Assessment",
            status=AssessmentStatus.PUBLISHED,
            total_duration_minutes=30
        )
        db.add(assess)
        db.commit()

        # Create invitation with token starting with ABC
        inv = CandidateInvitation(
            assessment_id=assess.id,
            org_id=test_org.id,
            email="replay.test@example.com",
            full_name="Replay Test",
            invitation_token="ABC_RANDOM_GENERATED_TOKEN_XYZ",
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
            status=CandidateStatus.SUBMITTED,
            system_check_passed=True
        )
        db.add(inv)
        db.commit()

        # Accessing instructions after submission must return 400 Bad Request
        inst_res = client.get(f"/api/v1/candidates/invitations/{inv.invitation_token}/instructions")
        assert inst_res.status_code == 400
        assert "already been submitted" in inst_res.json()["detail"].lower()

        # Attempting to start after submission must return 400 Bad Request
        start_res = client.post(f"/api/v1/attempts/start?invitation_token={inv.invitation_token}")
        assert start_res.status_code == 400
        assert "already been submitted" in start_res.json()["detail"].lower()

    def test_cross_tenant_idor_access_prevention(self, client, db, test_org, recruiter_headers):
        """
        Tests multi-tenant boundary enforcement:
        Recruiter from Org A cannot access Org B's assessments, attempts, or analytics.
        """
        # Create Org B
        org_b = Organization(name="Competitor Inc", slug="competitor", domain="competitor.com", is_active=True)
        db.add(org_b)
        db.flush()

        # Create Assessment in Org B
        assess_b = Assessment(
            org_id=org_b.id,
            title="Confidential Org B Assessment",
            status=AssessmentStatus.PUBLISHED,
            total_duration_minutes=60
        )
        db.add(assess_b)
        db.commit()

        # Recruiter from Org A attempts to view Org B analytics -> 403 Forbidden
        analytics_res = client.get(f"/api/v1/analytics/assessments/{assess_b.id}", headers=recruiter_headers)
        assert analytics_res.status_code == 403
        assert "Access denied" in analytics_res.json()["detail"]

        # Recruiter from Org A attempts to export Org B report -> 403 Forbidden
        export_res = client.get(f"/api/v1/analytics/assessments/{assess_b.id}/export?format=csv", headers=recruiter_headers)
        assert export_res.status_code == 403

        # Recruiter from Org A attempts to access Org B live proctor feed -> 403 Forbidden
        live_res = client.get(f"/api/v1/proctoring/assessments/{assess_b.id}/live-feed", headers=recruiter_headers)
        assert live_res.status_code == 403

        # Verify cross-tenant security audit event was logged
        audit_entry = db.query(SecurityAuditEvent).filter(
            SecurityAuditEvent.event_type == "CROSS_TENANT_ACCESS_BLOCKED"
        ).first()
        assert audit_entry is not None

    def test_sql_injection_resilience(self, client, db, test_org, recruiter_headers):
        """
        Tests that SQL injection strings in query parameters and search fields
        are safely parameterized and do not cause SQL syntax errors.
        """
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE assessments; --",
            "' UNION SELECT id, email, hashed_password FROM users --",
            "1' AND 1=(SELECT COUNT(*) FROM users) AND '1'='1"
        ]

        for payload in sql_payloads:
            # Question search with SQL injection payload
            res = client.get(f"/api/v1/questions?search={payload}", headers=recruiter_headers)
            assert res.status_code == 200
            assert isinstance(res.json(), list)

            # Assessment search with SQL injection payload
            assess_res = client.get(f"/api/v1/assessments?search={payload}", headers=recruiter_headers)
            assert assess_res.status_code == 200
            assert isinstance(assess_res.json(), list)

    def test_xss_payload_safety_in_responses(self, client, db, test_org, recruiter_headers):
        """
        Tests that script payloads stored in question text, explanations, or answers
        are handled strictly as data and do not trigger unexpected side effects.
        """
        xss_payload = "<script>alert('XSS-ATTACK-TEST')</script><img src=x onerror=alert(1)>"

        create_res = client.post("/api/v1/questions", json={
            "org_id": test_org.id,
            "title": f"XSS Test {xss_payload}",
            "description": xss_payload,
            "question_type": "MCQ_SINGLE",
            "difficulty": "EASY",
            "explanation": xss_payload,
            "options": [
                {"id": "opt_1", "text": xss_payload, "is_correct": True},
                {"id": "opt_2", "text": "Safe Option", "is_correct": False}
            ]
        }, headers=recruiter_headers)
        assert create_res.status_code == 201
        data = create_res.json()
        assert data["current_version"]["title"] == f"XSS Test {xss_payload}"
        assert data["current_version"]["options"][0]["text"] == xss_payload

    def test_health_check_probes(self, client):
        """
        Tests /health, /health/live, and /health/ready diagnostic endpoints.
        """
        # Liveness check
        live_res = client.get("/health/live")
        assert live_res.status_code == 200
        live_data = live_res.json()
        assert live_data["status"] == "healthy"
        assert "timestamp" in live_data

        # Readiness check
        ready_res = client.get("/health/ready")
        assert ready_res.status_code == 200
        ready_data = ready_res.json()
        assert ready_data["status"] == "healthy"
        assert ready_data["ready"] is True
        assert "database" in ready_data
        assert ready_data["database"] == "connected"
        assert ready_data["database_connected"] is True
        assert "database_latency_ms" in ready_data
        assert "sandbox" in ready_data

    def test_concurrent_autosave_idempotency_and_state_consistency(self, client, db, test_org, recruiter_headers):
        """
        Simulates concurrent and rapid autosave calls to verify answer state consistency
        and duplicate submission handling.
        """
        assess = Assessment(
            org_id=test_org.id,
            title="Concurrency Assessment",
            status=AssessmentStatus.PUBLISHED,
            total_duration_minutes=30,
            total_marks=10.0,
            passing_percentage=50.0
        )
        db.add(assess)
        db.flush()

        sec = Section(assessment_id=assess.id, title="Section 1", duration_minutes=30, order_index=0)
        db.add(sec)
        db.flush()

        q1 = Question(org_id=test_org.id, question_type=QuestionType.MCQ_SINGLE)
        db.add(q1)
        db.flush()
        qv1 = QuestionVersion(
            question_id=q1.id, version_number=1, title="Q1", description="Q1 description",
            question_type=QuestionType.MCQ_SINGLE, difficulty=DifficultyLevel.EASY,
            options=[{"id": "opt_1", "text": "Correct", "is_correct": True}]
        )
        db.add(qv1)
        db.flush()

        sq = SectionQuestion(section_id=sec.id, question_id=q1.id, question_version_id=qv1.id, positive_marks=10.0, negative_marks=0.0, order_index=0)
        db.add(sq)
        db.commit()

        # Create Candidate & Start
        inv = CandidateInvitation(
            assessment_id=assess.id,
            org_id=test_org.id,
            email="concurrent.cand@example.com",
            full_name="Concurrent Candidate",
            invitation_token="CONCURRENT_TOKEN_999",
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
            status=CandidateStatus.REGISTERED,
            system_check_passed=True
        )
        db.add(inv)
        db.commit()

        start_res = client.post(f"/api/v1/attempts/start?invitation_token={inv.invitation_token}")
        assert start_res.status_code == 200
        att_id = start_res.json()["attempt_id"]

        # Simulate 5 rapid sequential autosaves
        for i in range(5):
            save_res = client.post(f"/api/v1/attempts/{att_id}/answers/autosave", json={
                "answers": [
                    {
                        "question_id": q1.id,
                        "question_version_id": qv1.id,
                        "section_id": sec.id,
                        "selected_option_ids": ["opt_1"],
                        "time_spent_seconds": 10 + i
                    }
                ]
            })
            assert save_res.status_code == 200
            assert save_res.json()["success"] is True

        # Verify only 1 answer row exists in DB for this question (no duplicates)
        answer_rows = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == att_id,
            AttemptAnswer.question_id == q1.id
        ).all()
        assert len(answer_rows) == 1
        assert answer_rows[0].time_spent_seconds == 14

        # Submit attempt
        sub1 = client.post(f"/api/v1/attempts/{att_id}/submit", json={"final_answers": []})
        assert sub1.status_code == 200
        rcpt1 = sub1.json()["submission_receipt"]

        # Duplicate submit
        sub2 = client.post(f"/api/v1/attempts/{att_id}/submit", json={"final_answers": []})
        assert sub2.status_code == 200
        rcpt2 = sub2.json()["submission_receipt"]
        assert rcpt1 == rcpt2
