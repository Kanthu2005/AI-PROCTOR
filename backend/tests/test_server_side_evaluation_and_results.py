import io
import csv
import uuid
import pytest
from datetime import datetime, timedelta, timezone

from app.models.user import Organization, User, Role, SecurityAuditEvent
from app.models.assessment import Assessment, AssessmentRule, Section, SectionQuestion, AssessmentStatus
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus
from app.services.evaluation_service import EvaluationService
from app.services.analytics_service import AnalyticsService
from app.utils.security import hash_password, create_access_token


def make_auth_headers(user: User):
    token = create_access_token({
        "sub": user.id,
        "role": user.role.value,
        "org_id": user.org_id
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_org_recruiter_headers(db):
    other_org = Organization(name="Other Corp", slug=f"othercorp-{uuid.uuid4().hex[:6]}", domain="other.com", is_active=True)
    db.add(other_org)
    db.flush()
    user = User(
        email=f"other_{uuid.uuid4().hex[:6]}@other.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Other Recruiter",
        role=Role.RECRUITER,
        org_id=other_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return make_auth_headers(user)


def create_test_attempt(
    db, assessment_id, candidate_name="Test Candidate",
    candidate_email=None, started_at=None, submitted_at=None,
    total_score=0.0, total_max_marks=0.0, percentage=0.0,
    is_passed=False, status=AttemptStatus.SUBMITTED
):
    if not candidate_email:
        candidate_email = f"cand_{uuid.uuid4().hex[:6]}@example.com"
    assess = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    inv = CandidateInvitation(
        assessment_id=assessment_id,
        org_id=assess.org_id,
        email=candidate_email,
        full_name=candidate_name,
        invitation_token=f"inv-{uuid.uuid4().hex}",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2)
    )
    db.add(inv)
    db.flush()

    now_utc = datetime.now(timezone.utc)
    att = Attempt(
        invitation_id=inv.id,
        assessment_id=assessment_id,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        status=status,
        started_at=started_at or (now_utc - timedelta(minutes=20)),
        submitted_at=submitted_at or now_utc,
        server_expiry_at=now_utc + timedelta(minutes=40),
        total_score=total_score,
        total_max_marks=total_max_marks,
        percentage=percentage,
        is_passed=is_passed
    )
    db.add(att)
    db.flush()
    return att


@pytest.fixture
def eval_assessment_setup(db, test_org, recruiter_headers, author_headers, client):
    """
    Creates an assessment with:
    - Section 1 (Core Concepts): MCQ Single, MCQ Multiple-Select (PARTIAL_WITH_PENALTY)
    - Section 2 (Practical): Coding Question, Descriptive Question
    Section cut-offs: Section 1 cut-off 4.0, Section 2 cut-off 5.0
    Passing percentage: 50.0%
    """
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Comprehensive Evaluation Benchmark",
        "description": "Deterministic evaluation and results verification",
        "total_duration_minutes": 60,
        "total_marks": 25.0,
        "passing_percentage": 50.0
    }, headers=recruiter_headers)
    assert assess_res.status_code == 201
    a_id = assess_res.json()["id"]

    # Configure Rules
    client.put(f"/api/v1/assessments/{a_id}", json={
        "rules": {
            "negative_marking_enabled": True,
            "multiple_select_policy": "PARTIAL_WITH_PENALTY"
        }
    }, headers=recruiter_headers)

    # Section 1: Theory (Cut-off: 4.0, Total: 8.0)
    sec1 = Section(assessment_id=a_id, title="Theory & Concepts", duration_minutes=30, cut_off_marks=4.0, order_index=0)
    db.add(sec1)
    db.flush()

    # Section 2: Practical (Cut-off: 5.0, Total: 17.0)
    sec2 = Section(assessment_id=a_id, title="Practical & Design", duration_minutes=30, cut_off_marks=5.0, order_index=1)
    db.add(sec2)
    db.flush()

    # Q1: MCQ Single (Pos: 3.0, Neg: 1.0)
    q1 = Question(org_id=test_org.id, question_type=QuestionType.MCQ_SINGLE)
    db.add(q1)
    db.flush()
    qv1 = QuestionVersion(
        question_id=q1.id, version_number=1, title="Complexity MCQ", description="Time complexity of binary search",
        question_type=QuestionType.MCQ_SINGLE, difficulty=DifficultyLevel.EASY,
        options=[
            {"id": "opt_a", "text": "O(log n)", "is_correct": True},
            {"id": "opt_b", "text": "O(n)", "is_correct": False},
            {"id": "opt_c", "text": "O(1)", "is_correct": False}
        ]
    )
    db.add(qv1)
    db.flush()
    sq1 = SectionQuestion(section_id=sec1.id, question_id=q1.id, question_version_id=qv1.id, positive_marks=3.0, negative_marks=1.0, order_index=0)
    db.add(sq1)

    # Q2: MCQ Multiple Select (Pos: 5.0, Neg: 1.0)
    q2 = Question(org_id=test_org.id, question_type=QuestionType.MCQ_MULTIPLE)
    db.add(q2)
    db.flush()
    qv2 = QuestionVersion(
        question_id=q2.id, version_number=1, title="Data Structure Properties", description="Which are linear?",
        question_type=QuestionType.MCQ_MULTIPLE, difficulty=DifficultyLevel.MEDIUM,
        options=[
            {"id": "opt_arr", "text": "Array", "is_correct": True},
            {"id": "opt_list", "text": "Linked List", "is_correct": True},
            {"id": "opt_tree", "text": "Binary Tree", "is_correct": False},
            {"id": "opt_graph", "text": "Graph", "is_correct": False}
        ]
    )
    db.add(qv2)
    db.flush()
    sq2 = SectionQuestion(section_id=sec1.id, question_id=q2.id, question_version_id=qv2.id, positive_marks=5.0, negative_marks=1.0, order_index=1)
    db.add(sq2)

    # Q3: Coding Question (Pos: 10.0, Neg: 0.0)
    q3 = Question(org_id=test_org.id, question_type=QuestionType.CODING)
    db.add(q3)
    db.flush()
    qv3 = QuestionVersion(
        question_id=q3.id, version_number=1, title="Square Function", description="Return square of input",
        question_type=QuestionType.CODING, difficulty=DifficultyLevel.EASY,
        coding_details={
            "language": "python",
            "test_cases": [
                {"input": "3", "expected_output": "9", "is_hidden": False},
                {"input": "4", "expected_output": "16", "is_hidden": False},
                {"input": "-5", "expected_output": "25", "is_hidden": True},
                {"input": "0", "expected_output": "0", "is_hidden": True}
            ]
        }
    )
    db.add(qv3)
    db.flush()
    sq3 = SectionQuestion(section_id=sec2.id, question_id=q3.id, question_version_id=qv3.id, positive_marks=10.0, negative_marks=0.0, order_index=0)
    db.add(sq3)

    # Q4: Descriptive Question (Pos: 7.0, Neg: 0.0)
    q4 = Question(org_id=test_org.id, question_type=QuestionType.DESCRIPTIVE)
    db.add(q4)
    db.flush()
    qv4 = QuestionVersion(
        question_id=q4.id, version_number=1, title="Database Normalization", description="Explain 1NF, 2NF and 3NF with examples",
        question_type=QuestionType.DESCRIPTIVE, difficulty=DifficultyLevel.HARD,
        explanation="Normalization redundancy atomicity functional dependency candidate keys foreign keys transitive"
    )
    db.add(qv4)
    db.flush()
    sq4 = SectionQuestion(section_id=sec2.id, question_id=q4.id, question_version_id=qv4.id, positive_marks=7.0, negative_marks=0.0, order_index=1)
    db.add(sq4)

    db.commit()

    return {
        "assessment_id": a_id,
        "sec1_id": sec1.id,
        "sec2_id": sec2.id,
        "q1_id": q1.id, "qv1_id": qv1.id,
        "q2_id": q2.id, "qv2_id": qv2.id,
        "q3_id": q3.id, "qv3_id": qv3.id,
        "q4_id": q4.id, "qv4_id": qv4.id
    }


def test_mcq_scoring_and_unanswered_policies():
    """
    Test deterministic MCQ scoring, unanswered policy (0.0 marks),
    negative marking enabled vs disabled, and 2-decimal rounding.
    """
    # 1. Single-select: correct
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_1"],
        correct_option_ids=["opt_1"],
        positive_marks=3.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        is_multiple_select=False
    )
    assert is_corr is True
    assert score == 3.0

    # 2. Single-select: incorrect with negative marks
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_2"],
        correct_option_ids=["opt_1"],
        positive_marks=3.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        is_multiple_select=False
    )
    assert is_corr is False
    assert score == -1.0

    # 3. Single-select: incorrect with negative marks disabled
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_2"],
        correct_option_ids=["opt_1"],
        positive_marks=3.0,
        negative_marks=1.0,
        negative_marking_enabled=False,
        is_multiple_select=False
    )
    assert is_corr is False
    assert score == 0.0

    # 4. Unanswered policy: ALWAYS 0.0 marks, never penalized
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=[],
        correct_option_ids=["opt_1"],
        positive_marks=3.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        is_multiple_select=False
    )
    assert is_corr is False
    assert score == 0.0

    # 5. Rounding check (e.g., 10 / 3 = 3.33)
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_1"],
        correct_option_ids=["opt_1"],
        positive_marks=10.0 / 3.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        is_multiple_select=False
    )
    assert is_corr is True
    assert score == 3.33


def test_multiple_select_policies():
    """
    Test multiple-select policies:
    - ALL_OR_NOTHING
    - PARTIAL_WITH_PENALTY
    """
    correct_opts = ["opt_a", "opt_b"]

    # --- ALL_OR_NOTHING ---
    # Exact match
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_a", "opt_b"],
        correct_option_ids=correct_opts,
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        multiple_select_policy="ALL_OR_NOTHING",
        is_multiple_select=True
    )
    assert is_corr is True
    assert score == 4.0

    # Partial selection with ALL_OR_NOTHING yields penalty
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_a"],
        correct_option_ids=correct_opts,
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        multiple_select_policy="ALL_OR_NOTHING",
        is_multiple_select=True
    )
    assert is_corr is False
    assert score == -1.0

    # Unanswered under ALL_OR_NOTHING yields 0.0
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=[],
        correct_option_ids=correct_opts,
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        multiple_select_policy="ALL_OR_NOTHING",
        is_multiple_select=True
    )
    assert is_corr is False
    assert score == 0.0

    # --- PARTIAL_WITH_PENALTY ---
    # 1 out of 2 correct, 0 false positives -> (1/2) * 4.0 = 2.0
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_a"],
        correct_option_ids=correct_opts,
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        multiple_select_policy="PARTIAL_WITH_PENALTY",
        is_multiple_select=True
    )
    assert is_corr is False
    assert score == 2.0

    # 1 out of 2 correct, 1 false positive -> 2.0 - 1.0 (penalty) = 1.0
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_a", "opt_wrong"],
        correct_option_ids=correct_opts,
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        multiple_select_policy="PARTIAL_WITH_PENALTY",
        is_multiple_select=True
    )
    assert is_corr is False
    assert score == 1.0

    # 0 correct, 2 false positives -> bounded to -negative_marks (-1.0)
    is_corr, score = EvaluationService.evaluate_mcq(
        selected_option_ids=["opt_wrong1", "opt_wrong2"],
        correct_option_ids=correct_opts,
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True,
        multiple_select_policy="PARTIAL_WITH_PENALTY",
        is_multiple_select=True
    )
    assert is_corr is False
    assert score == -1.0


def test_coding_score_integration_trusted_runner_only():
    """
    Coding score must be evaluated strictly through server-side CodingSandboxRunner.
    Partial credit based on passed test cases.
    """
    test_cases = [
        {"input": "2", "expected_output": "4"},
        {"input": "3", "expected_output": "9"},
        {"input": "4", "expected_output": "16"},
        {"input": "5", "expected_output": "25"}
    ]

    code = """
import sys
x = int(sys.stdin.read().strip())
if x in [2, 3]:
    print(x * x)
else:
    print(0)
"""
    is_corr, score, exec_res = EvaluationService.evaluate_coding_question(
        code_response=code,
        test_cases=test_cases,
        positive_marks=10.0
    )
    assert is_corr is False
    assert score == 5.0  # 2/4 * 10 = 5.0
    assert exec_res["passed_test_cases"] == 2
    assert exec_res["total_test_cases"] == 4


def test_section_cutoffs_and_pass_fail_rules(db, test_org, eval_assessment_setup):
    """
    Test section scores, cut-off enforcement, and overall passing percentage rules.
    If a candidate fails a section cut-off, overall attempt must be FAILED even if
    total percentage exceeds the passing threshold.
    """
    setup = eval_assessment_setup
    attempt = create_test_attempt(db, setup["assessment_id"], candidate_name="Alice Candidate")

    # Section 1 (cut-off: 4.0): Candidate gets Q1 correct (3.0) and Q2 partial (2.5) -> Section 1 = 5.5 (PASSED)
    ans1 = AttemptAnswer(
        attempt_id=attempt.id, question_id=setup["q1_id"], question_version_id=setup["qv1_id"],
        section_id=setup["sec1_id"], selected_option_ids=["opt_a"]
    )
    ans2 = AttemptAnswer(
        attempt_id=attempt.id, question_id=setup["q2_id"], question_version_id=setup["qv2_id"],
        section_id=setup["sec1_id"], selected_option_ids=["opt_arr"] # 1/2 correct = 2.5 marks
    )

    # Section 2 (cut-off: 5.0): Candidate gets Q3 0 marks (empty code) and Q4 unevaluated -> Section 2 = 0.0 (FAILED cut-off)
    ans3 = AttemptAnswer(
        attempt_id=attempt.id, question_id=setup["q3_id"], question_version_id=setup["qv3_id"],
        section_id=setup["sec2_id"], code_response=""
    )
    ans4 = AttemptAnswer(
        attempt_id=attempt.id, question_id=setup["q4_id"], question_version_id=setup["qv4_id"],
        section_id=setup["sec2_id"], text_response="Normalization avoids redundancy"
    )

    db.add_all([ans1, ans2, ans3, ans4])
    db.commit()

    # Authoritative server-side evaluation
    eval_att = EvaluationService.evaluate_attempt(db, attempt.id)

    assert eval_att.section_scores[setup["sec1_id"]]["is_passed"] is True
    assert eval_att.section_scores[setup["sec1_id"]]["score"] == 5.5
    assert eval_att.section_scores[setup["sec2_id"]]["is_passed"] is False  # 0.0 < 5.0 cut-off
    assert eval_att.is_passed is False  # Failed section cut-off!
    assert eval_att.evaluation_status == "REQUIRES_MANUAL_REVIEW"


def test_manual_descriptive_evaluation_and_audit_trail(db, test_org, eval_assessment_setup, client, recruiter_headers, recruiter):
    """
    Test manual evaluation of descriptive question:
    - Bounds validation (reject > max_marks and < 0)
    - Reviewer comments
    - Score and pass/fail recalculation
    - Audit trail logging (MANUAL_EVALUATION_MODIFIED)
    """
    setup = eval_assessment_setup
    attempt = create_test_attempt(db, setup["assessment_id"], candidate_name="Bob Candidate")

    # Section 1: Q1 correct (3.0), Q2 correct (5.0) -> Section 1 = 8.0 (Passes 4.0 cut-off)
    ans1 = AttemptAnswer(attempt_id=attempt.id, question_id=setup["q1_id"], question_version_id=setup["qv1_id"], section_id=setup["sec1_id"], selected_option_ids=["opt_a"])
    ans2 = AttemptAnswer(attempt_id=attempt.id, question_id=setup["q2_id"], question_version_id=setup["qv2_id"], section_id=setup["sec1_id"], selected_option_ids=["opt_arr", "opt_list"])

    # Section 2: Q3 code correct (10.0), Q4 descriptive response awaiting manual evaluation
    code = "import sys\nx = int(sys.stdin.read().strip())\nprint(x * x)"
    ans3 = AttemptAnswer(attempt_id=attempt.id, question_id=setup["q3_id"], question_version_id=setup["qv3_id"], section_id=setup["sec2_id"], code_response=code)
    ans4 = AttemptAnswer(attempt_id=attempt.id, question_id=setup["q4_id"], question_version_id=setup["qv4_id"], section_id=setup["sec2_id"], text_response="1NF has atomic values. 2NF removes partial dependency. 3NF removes transitive dependency.")

    db.add_all([ans1, ans2, ans3, ans4])
    db.commit()

    # Initial evaluation
    EvaluationService.evaluate_attempt(db, attempt.id)

    # 1. Reject invalid marks (> max_marks=7.0)
    res_invalid = client.post(
        f"/api/v1/attempts/{attempt.id}/answers/{setup['q4_id']}/evaluate",
        json={"marks_awarded": 15.0, "reviewer_comments": "Too high"},
        headers=recruiter_headers
    )
    assert res_invalid.status_code == 400

    # 2. Reject negative marks
    res_neg = client.post(
        f"/api/v1/attempts/{attempt.id}/answers/{setup['q4_id']}/evaluate",
        json={"marks_awarded": -2.0, "reviewer_comments": "Negative"},
        headers=recruiter_headers
    )
    assert res_neg.status_code == 400

    # 3. Valid evaluation
    res_valid = client.post(
        f"/api/v1/attempts/{attempt.id}/answers/{setup['q4_id']}/evaluate",
        json={"marks_awarded": 6.5, "reviewer_comments": "Comprehensive explanation of normalization."},
        headers=recruiter_headers
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["marks_awarded"] == 6.5
    assert data["reviewer_comments"] == "Comprehensive explanation of normalization."
    assert data["is_manually_evaluated"] is True

    # Verify attempt score updated: Section 1 (8.0) + Section 2 (10.0 + 6.5 = 16.5) = 24.5 / 25.0 (98%)
    db.refresh(attempt)
    assert attempt.total_score == 24.5
    assert attempt.is_passed is True
    assert attempt.evaluation_status == "FULLY_EVALUATED"

    # Verify Audit Trail
    audit_event = db.query(SecurityAuditEvent).filter(
        SecurityAuditEvent.event_type == "MANUAL_EVALUATION_MODIFIED",
        SecurityAuditEvent.user_id == recruiter.id
    ).first()
    assert audit_event is not None
    details = audit_event.details
    if isinstance(details, str):
        import json
        details = json.loads(details)
    assert details["attempt_id"] == attempt.id
    assert details["new_marks"] == 6.5


def test_ai_suggested_descriptive_score_requires_human_confirmation(db, test_org, eval_assessment_setup, client, recruiter_headers):
    """
    Test that AI suggested score provides suggestion, confidence, and rationale,
    but NEVER changes official marks without explicit human confirmation.
    """
    setup = eval_assessment_setup
    attempt = create_test_attempt(db, setup["assessment_id"], candidate_name="Charlie Candidate")

    ans = AttemptAnswer(
        attempt_id=attempt.id,
        question_id=setup["q4_id"],
        question_version_id=setup["qv4_id"],
        section_id=setup["sec2_id"],
        text_response="Database normalization minimizes redundancy and dependency by organizing fields and table of a database. Key concepts are atomicity, functional dependency, candidate keys, foreign keys, and transitive dependency removal.",
        marks_awarded=0.0,
        is_manually_evaluated=False
    )
    db.add(ans)
    db.commit()

    # Request AI suggested score
    res = client.post(
        f"/api/v1/attempts/{attempt.id}/answers/{setup['q4_id']}/suggest-score",
        headers=recruiter_headers
    )
    assert res.status_code == 200
    suggestion = res.json()
    assert suggestion["requires_human_confirmation"] is True
    assert suggestion["suggested_marks"] > 0.0
    assert suggestion["confidence"] > 0.5
    assert "rationale" in suggestion

    # Verify official marks remain 0.0 until recruiter confirms
    db.refresh(ans)
    assert ans.marks_awarded == 0.0
    assert ans.is_manually_evaluated is False
    assert ans.ai_suggested_marks == suggestion["suggested_marks"]


def test_candidate_rankings_with_compound_tie_breakers(db, test_org, eval_assessment_setup):
    """
    Test compound tie-breaking rules:
    1. Higher Score
    2. Higher Accuracy
    3. Less Time Taken
    4. Earlier Submission Timestamp
    """
    setup = eval_assessment_setup
    base_time = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)

    # Candidate 1: Score 80.0, Accuracy 100% (4/4), Time 500s
    att1 = create_test_attempt(
        db, setup["assessment_id"], candidate_name="Cand 1", candidate_email="c1@example.com",
        started_at=base_time, submitted_at=base_time + timedelta(seconds=500),
        total_score=80.0, total_max_marks=100.0, percentage=80.0, is_passed=True
    )
    # Candidate 2: Score 80.0, Accuracy 80% (4/5), Time 400s
    att2 = create_test_attempt(
        db, setup["assessment_id"], candidate_name="Cand 2", candidate_email="c2@example.com",
        started_at=base_time, submitted_at=base_time + timedelta(seconds=400),
        total_score=80.0, total_max_marks=100.0, percentage=80.0, is_passed=True
    )
    # Candidate 3: Score 80.0, Accuracy 80% (4/5), Time 600s
    att3 = create_test_attempt(
        db, setup["assessment_id"], candidate_name="Cand 3", candidate_email="c3@example.com",
        started_at=base_time, submitted_at=base_time + timedelta(seconds=600),
        total_score=80.0, total_max_marks=100.0, percentage=80.0, is_passed=True
    )
    # Candidate 4: Score 60.0
    att4 = create_test_attempt(
        db, setup["assessment_id"], candidate_name="Cand 4", candidate_email="c4@example.com",
        started_at=base_time, submitted_at=base_time + timedelta(seconds=300),
        total_score=60.0, total_max_marks=100.0, percentage=60.0, is_passed=True
    )

    # Answers for att1: 4 correct
    for i in range(4):
        db.add(AttemptAnswer(attempt_id=att1.id, question_id=f"q_{i}", question_version_id=f"qv_{i}", section_id="s1", is_correct=True, marks_awarded=20.0))

    # Answers for att2: 4 correct, 1 incorrect (accuracy = 80%)
    for i in range(4):
        db.add(AttemptAnswer(attempt_id=att2.id, question_id=f"q_{i}", question_version_id=f"qv_{i}", section_id="s1", is_correct=True, marks_awarded=20.0))
    db.add(AttemptAnswer(attempt_id=att2.id, question_id="q_5", question_version_id="qv_5", section_id="s1", is_correct=False, marks_awarded=0.0))

    # Answers for att3: 4 correct, 1 incorrect (accuracy = 80%)
    for i in range(4):
        db.add(AttemptAnswer(attempt_id=att3.id, question_id=f"q_{i}", question_version_id=f"qv_{i}", section_id="s1", is_correct=True, marks_awarded=20.0))
    db.add(AttemptAnswer(attempt_id=att3.id, question_id="q_5", question_version_id="qv_5", section_id="s1", is_correct=False, marks_awarded=0.0))

    # Answers for att4: 3 correct
    for i in range(3):
        db.add(AttemptAnswer(attempt_id=att4.id, question_id=f"q_{i}", question_version_id=f"qv_{i}", section_id="s1", is_correct=True, marks_awarded=20.0))

    db.commit()

    # Compute official rankings
    ranked = AnalyticsService.compute_rankings_and_percentiles(db, setup["assessment_id"])

    # Cand 1 has highest accuracy (100% vs 80%) -> Rank 1
    # Cand 2 has 80% accuracy and completed in 400s (< 600s) -> Rank 2
    # Cand 3 has 80% accuracy and completed in 600s -> Rank 3
    # Cand 4 has lower score (60.0) -> Rank 4
    ranks = {att.candidate_name: att.rank for att in ranked}
    assert ranks["Cand 1"] == 1
    assert ranks["Cand 2"] == 2
    assert ranks["Cand 3"] == 3
    assert ranks["Cand 4"] == 4

    # Percentiles
    percentiles = {att.candidate_name: att.percentile for att in ranked}
    assert percentiles["Cand 1"] == 100.0  # 4/4 score <= 80
    assert percentiles["Cand 4"] == 25.0   # 1/4 score <= 60


def test_question_analytics_and_score_distributions(db, test_org, eval_assessment_setup, client, recruiter_headers):
    """
    Test question-level analytics (pass rate, discrimination index, average time spent)
    and score distribution percentage buckets.
    """
    setup = eval_assessment_setup
    res = client.get(f"/api/v1/analytics/assessments/{setup['assessment_id']}", headers=recruiter_headers)
    assert res.status_code == 200
    data = res.json()

    assert "question_analytics" in data
    assert len(data["question_analytics"]) > 0
    assert "score_distribution" in data
    assert "0-20%" in data["score_distribution"]
    assert "81-100%" in data["score_distribution"]


def test_authorized_csv_and_pdf_report_export(db, test_org, eval_assessment_setup, client, recruiter_headers, candidate_headers, other_org_recruiter_headers):
    """
    Test report export:
    - Recruiter can export CSV -> 200 text/csv
    - Recruiter can export PDF -> 200 application/pdf (%PDF-1.4 header)
    - Candidate is forbidden -> 403
    - Recruiter from other org is forbidden -> 403 (Tenant isolation)
    - Audit event logged
    """
    setup = eval_assessment_setup

    # 1. Export CSV by authorized recruiter
    res_csv = client.get(f"/api/v1/analytics/assessments/{setup['assessment_id']}/export?format=csv", headers=recruiter_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    csv_text = res_csv.text
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)
    assert "Rank" in header
    assert "Candidate Name" in header
    assert "Total Score" in header

    # 2. Export PDF by authorized recruiter
    res_pdf = client.get(f"/api/v1/analytics/assessments/{setup['assessment_id']}/export?format=pdf", headers=recruiter_headers)
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert res_pdf.content.startswith(b"%PDF-1.4")

    # 3. Candidate unauthorized access
    res_cand = client.get(f"/api/v1/analytics/assessments/{setup['assessment_id']}/export?format=csv", headers=candidate_headers)
    assert res_cand.status_code == 403

    # 4. Cross-tenant unauthorized recruiter access
    res_unauth = client.get(f"/api/v1/analytics/assessments/{setup['assessment_id']}/export?format=csv", headers=other_org_recruiter_headers)
    assert res_unauth.status_code == 403

    # 5. Verify audit event
    audit = db.query(SecurityAuditEvent).filter(
        SecurityAuditEvent.event_type == "ASSESSMENT_REPORT_EXPORTED"
    ).first()
    assert audit is not None


def test_idempotent_evaluation_prevents_duplicate_results(db, test_org, eval_assessment_setup):
    """
    Evaluating an already fully evaluated attempt must be idempotent
    and never corrupt or duplicate scores.
    """
    setup = eval_assessment_setup
    attempt = create_test_attempt(db, setup["assessment_id"], candidate_name="Idempotent Test Candidate")

    ans = AttemptAnswer(
        attempt_id=attempt.id,
        question_id=setup["q1_id"],
        question_version_id=setup["qv1_id"],
        section_id=setup["sec1_id"],
        selected_option_ids=["opt_a"]
    )
    db.add(ans)
    db.commit()

    # First evaluation
    eval1 = EvaluationService.evaluate_attempt(db, attempt.id)
    score1 = eval1.total_score
    status1 = eval1.evaluation_status

    # Second evaluation without recompute_all
    eval2 = EvaluationService.evaluate_attempt(db, attempt.id, recompute_all=False)
    assert eval2.total_score == score1
    assert eval2.evaluation_status == status1
