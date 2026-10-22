import pytest
from app.models.user import User, Role, Organization
from app.models.assessment import Assessment, AssessmentStatus
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus
from app.models.question import Question, QuestionType
from app.services.code_similarity_service import CodeSimilarityService
from datetime import datetime, timedelta, timezone


def test_code_similarity_normalization_and_comparison():
    code1 = """
    # Solution 1
    def two_sum(nums, target):
        lookup = {}
        for i, val in enumerate(nums):
            diff = target - val
            if diff in lookup:
                return [lookup[diff], i]
            lookup[val] = i
        return []
    """

    code2 = """
    // Solution 2 with comments and formatting
    def two_sum(nums, target):
        lookup = {}
        for i, val in enumerate(nums):
            diff = target - val
            if diff in lookup:
                return [lookup[diff], i]
            lookup[val] = i
        return []
    """

    sim = CodeSimilarityService.calculate_similarity(code1, code2)
    # Since only comments differ, normalized code is identical
    assert sim == 1.0


def test_code_similarity_different_solutions():
    code1 = "def solve(n): return n * 2"
    code2 = "def solve(arr): return sorted([x for x in arr if x > 0])"
    sim = CodeSimilarityService.calculate_similarity(code1, code2)
    assert sim < 0.60


def test_code_similarity_cohort_endpoint(client, db, test_org, recruiter_headers):
    # 1. Create assessment
    assessment = Assessment(
        org_id=test_org.id,
        title="Plagiarism Analysis Cohort",
        total_duration_minutes=60,
        total_marks=20.0,
        passing_percentage=50.0,
        status=AssessmentStatus.PUBLISHED
    )
    db.add(assessment)
    db.flush()

    # 2. Create coding question
    question = Question(
        org_id=test_org.id,
        question_type=QuestionType.CODING
    )
    db.add(question)
    db.flush()

    # 3. Create two candidate attempts with identical/similar submissions
    inv1 = CandidateInvitation(
        assessment_id=assessment.id,
        org_id=test_org.id,
        email="cand1@test.com",
        full_name="Candidate One",
        invitation_token="token-sim-1",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        status=CandidateStatus.SUBMITTED
    )
    inv2 = CandidateInvitation(
        assessment_id=assessment.id,
        org_id=test_org.id,
        email="cand2@test.com",
        full_name="Candidate Two",
        invitation_token="token-sim-2",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        status=CandidateStatus.SUBMITTED
    )
    db.add_all([inv1, inv2])
    db.flush()

    att1 = Attempt(
        invitation_id=inv1.id,
        assessment_id=assessment.id,
        candidate_email=inv1.email,
        candidate_name=inv1.full_name,
        status=AttemptStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc)
    )
    att2 = Attempt(
        invitation_id=inv2.id,
        assessment_id=assessment.id,
        candidate_email=inv2.email,
        candidate_name=inv2.full_name,
        status=AttemptStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc)
    )
    db.add_all([att1, att2])
    db.flush()

    ans1 = AttemptAnswer(
        attempt_id=att1.id,
        question_id=question.id,
        question_version_id="ver-1",
        section_id="sec-1",
        code_response="def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n - 1)"
    )
    ans2 = AttemptAnswer(
        attempt_id=att2.id,
        question_id=question.id,
        question_version_id="ver-1",
        section_id="sec-1",
        code_response="# Factorial\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"
    )
    db.add_all([ans1, ans2])
    db.commit()

    # 4. Request code similarity analysis
    res = client.get(
        f"/api/v1/analytics/assessments/{assessment.id}/code-similarity?threshold=0.70",
        headers=recruiter_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["assessment_id"] == assessment.id
    assert data["review_signal_only"] is True
    assert "disclaimer" in data
    assert len(data["flagged_pairs"]) >= 1

    pair = data["flagged_pairs"][0]
    assert pair["similarity_score"] >= 0.85
    assert pair["review_tier"] == "SUSPICIOUS_MATCH"
    assert pair["investigation_recommended"] is True
