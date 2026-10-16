import pytest
from datetime import datetime, timedelta, timezone
from app.models.attempt import Attempt, AttemptStatus, RiskLevel, HumanReviewStatus
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.services.sandbox_service import CodingSandboxRunner
from app.services.analytics_service import AnalyticsService


def test_coding_sandbox_executes_valid_code():
    code = (
        "import sys\n"
        "data = sys.stdin.read().strip().split()\n"
        "nums = [int(x) for x in data]\n"
        "print(sum(nums))\n"
    )
    test_cases = [
        {"input": "1 2 3", "expected_output": "6", "is_hidden": False},
        {"input": "10 20 30", "expected_output": "60", "is_hidden": True}
    ]
    result = CodingSandboxRunner.execute_code(code, test_cases, timeout_seconds=2)
    assert result["total_test_cases"] == 2
    assert result["passed_test_cases"] == 2
    assert result["all_passed"] is True


def test_coding_sandbox_detects_mismatch():
    code = "print('42')\n"
    test_cases = [
        {"input": "", "expected_output": "100", "is_hidden": False}
    ]
    result = CodingSandboxRunner.execute_code(code, test_cases, timeout_seconds=2)
    assert result["passed_test_cases"] == 0
    assert result["all_passed"] is False


def test_coding_sandbox_enforces_timeout():
    code = "while True: pass\n"
    test_cases = [{"input": "", "expected_output": "done"}]
    result = CodingSandboxRunner.execute_code(code, test_cases, timeout_seconds=1)
    assert result["passed_test_cases"] == 0
    assert "Time Limit Exceeded" in result["results"][0]["error"]


def test_analytics_ranking_and_tie_breakers(db, test_org):
    # Setup test assessment
    from app.models.assessment import Assessment
    assess = Assessment(
        org_id=test_org.id,
        title="Analytics Test Assessment",
        passing_percentage=50.0
    )
    db.add(assess)
    db.flush()

    now = datetime.now(timezone.utc)

    # Candidate A: Score 90, 30 mins
    invA = CandidateInvitation(
        assessment_id=assess.id, org_id=test_org.id, email="a@test.com",
        full_name="Alice", invitation_token="tokA", expires_at=now + timedelta(days=1),
        status=CandidateStatus.SUBMITTED
    )
    db.add(invA)
    db.flush()
    attA = Attempt(
        invitation_id=invA.id, assessment_id=assess.id, candidate_email=invA.email,
        candidate_name=invA.full_name, status=AttemptStatus.SUBMITTED,
        started_at=now - timedelta(minutes=30), submitted_at=now,
        total_score=90.0, total_max_marks=100.0, percentage=90.0, is_passed=True
    )
    db.add(attA)

    # Candidate B: Score 90, 20 mins (Faster than A -> Should win tie-breaker!)
    invB = CandidateInvitation(
        assessment_id=assess.id, org_id=test_org.id, email="b@test.com",
        full_name="Bob", invitation_token="tokB", expires_at=now + timedelta(days=1),
        status=CandidateStatus.SUBMITTED
    )
    db.add(invB)
    db.flush()
    attB = Attempt(
        invitation_id=invB.id, assessment_id=assess.id, candidate_email=invB.email,
        candidate_name=invB.full_name, status=AttemptStatus.SUBMITTED,
        started_at=now - timedelta(minutes=20), submitted_at=now,
        total_score=90.0, total_max_marks=100.0, percentage=90.0, is_passed=True
    )
    db.add(attB)

    # Candidate C: Score 50, 15 mins
    invC = CandidateInvitation(
        assessment_id=assess.id, org_id=test_org.id, email="c@test.com",
        full_name="Charlie", invitation_token="tokC", expires_at=now + timedelta(days=1),
        status=CandidateStatus.SUBMITTED
    )
    db.add(invC)
    db.flush()
    attC = Attempt(
        invitation_id=invC.id, assessment_id=assess.id, candidate_email=invC.email,
        candidate_name=invC.full_name, status=AttemptStatus.SUBMITTED,
        started_at=now - timedelta(minutes=15), submitted_at=now,
        total_score=50.0, total_max_marks=100.0, percentage=50.0, is_passed=True
    )
    db.add(attC)

    db.commit()

    # Compute rankings
    ranked = AnalyticsService.compute_rankings_and_percentiles(db, assess.id)
    assert len(ranked) == 3

    # Bob took 20 mins, Alice took 30 mins -> Bob should be Rank 1!
    assert ranked[0].candidate_name == "Bob"
    assert ranked[0].rank == 1
    assert ranked[1].candidate_name == "Alice"
    assert ranked[1].rank == 2
    assert ranked[2].candidate_name == "Charlie"
    assert ranked[2].rank == 3

    # Check percentiles
    assert ranked[0].percentile == 100.0  # Bob & Alice at top
    assert ranked[2].percentile == pytest.approx(33.33, 0.1)


def test_assessment_analytics_api(client, db, test_org, recruiter_headers):
    from app.models.assessment import Assessment
    assess = Assessment(
        org_id=test_org.id,
        title="Summary Analytics Assessment",
        passing_percentage=50.0
    )
    db.add(assess)
    db.commit()
    db.refresh(assess)

    res = client.get(f"/api/v1/analytics/assessments/{assess.id}", headers=recruiter_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["assessment_id"] == assess.id
    assert "leaderboard" in data
    assert "question_analytics" in data
