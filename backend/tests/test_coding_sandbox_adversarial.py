import time
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.models.assessment import Assessment, AssessmentStatus
from app.models.attempt import Attempt, AttemptStatus
from app.models.candidate import CandidateInvitation
from app.models.coding import CodingSubmission, SubmissionStatus
from app.services.sandbox_service import CodingSandboxRunner, SandboxRateLimiter
from app.config import settings


@pytest.fixture
def coding_question_fixture(db, test_org):
    q = Question(org_id=test_org.id, question_type=QuestionType.CODING)
    db.add(q)
    db.flush()

    qv = QuestionVersion(
        question_id=q.id,
        version_number=1,
        title="Sum of Two Numbers",
        description="Read two space-separated integers from stdin and print their sum.",
        question_type=QuestionType.CODING,
        difficulty=DifficultyLevel.EASY,
        coding_details={
            "language": "python",
            "input_format": "Two integers a and b separated by space",
            "output_format": "Single integer representing sum",
            "constraints": "-10^9 <= a, b <= 10^9",
            "time_limit_seconds": 2,
            "memory_limit_mb": 128,
            "starter_code": "import sys\n# Read input\n",
            "test_cases": [
                {"input": "2 3", "expected_output": "5", "is_hidden": False, "explanation": "2 + 3 = 5"},
                {"input": "-1 1", "expected_output": "0", "is_hidden": False, "explanation": "-1 + 1 = 0"},
                {"input": "100 200", "expected_output": "300", "is_hidden": True},
                {"input": "-50 -50", "expected_output": "-100", "is_hidden": True}
            ]
        }
    )
    db.add(qv)
    db.commit()
    db.refresh(q)
    return q


def test_adversarial_infinite_loop_timeout():
    """
    Adversarial Test 1: Infinite loop must be terminated cleanly after timeout.
    Must never hang the API process and must return TIME_LIMIT_EXCEEDED.
    """
    code = """
import sys
# Infinite loop attempt
while True:
    x = 1 + 1
"""
    test_cases = [{"input": "test", "expected_output": "output", "is_hidden": False}]
    start = time.time()
    res = CodingSandboxRunner.execute_code(code, test_cases, timeout_seconds=1)
    duration = time.time() - start

    assert duration < 3.0  # Must be killed quickly
    assert res["passed_test_cases"] == 0
    assert res["failure_type"] == "TIME_LIMIT_EXCEEDED"
    assert "Time Limit Exceeded" in res["results"][0]["error"]


def test_adversarial_excessive_output_flooding():
    """
    Adversarial Test 2: Runaway output generation must be bounded/capped to 64KB
    and report OUTPUT_LIMIT_EXCEEDED without exhausting disk or pipe buffers.
    """
    code = """
import sys
# Output flooding attempt
for _ in range(50000):
    sys.stdout.write("SPAM_DATA_" * 10)
"""
    test_cases = [{"input": "test", "expected_output": "expected", "is_hidden": False}]
    res = CodingSandboxRunner.execute_code(code, test_cases, timeout_seconds=2)

    assert res["passed_test_cases"] == 0
    assert res["failure_type"] == "OUTPUT_LIMIT_EXCEEDED"
    assert "Output Limit Exceeded" in res["results"][0]["error"]


def test_adversarial_memory_exhaustion():
    """
    Adversarial Test 3: Large memory allocation must be caught and bounded,
    reporting MEMORY_LIMIT_EXCEEDED without crashing the host process.
    """
    code = """
import sys
# Massive memory allocation attempt (e.g. 10 billion integers -> ~80GB RAM, triggers MemoryError)
arr = [0] * (10 ** 10)
"""
    test_cases = [{"input": "test", "expected_output": "expected", "is_hidden": False}]
    res = CodingSandboxRunner.execute_code(code, test_cases, timeout_seconds=2, memory_limit_mb=64)

    assert res["passed_test_cases"] == 0
    # Must report memory limit exceeded without crashing
    assert res["failure_type"] == "MEMORY_LIMIT_EXCEEDED"


def test_adversarial_network_access_denial():
    """
    Adversarial Test 4: Network access (sockets, urllib) must be strictly denied by default.
    Must report SECURITY_VIOLATION.
    """
    # 1. Socket connection attempt
    code_socket = """
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("8.8.8.8", 53))
"""
    test_cases = [{"input": "", "expected_output": "", "is_hidden": False}]
    res_sock = CodingSandboxRunner.execute_code(code_socket, test_cases, timeout_seconds=2)
    assert res_sock["passed_test_cases"] == 0
    assert res_sock["failure_type"] == "SECURITY_VIOLATION"
    assert "SecurityViolation" in res_sock["results"][0]["error"] or "Network access is denied" in res_sock["results"][0]["error"]

    # 2. Urllib http request attempt
    code_urllib = """
import urllib.request
urllib.request.urlopen("http://169.254.169.254/latest/meta-data/")
"""
    res_url = CodingSandboxRunner.execute_code(code_urllib, test_cases, timeout_seconds=2)
    assert res_url["passed_test_cases"] == 0
    assert res_url["failure_type"] == "SECURITY_VIOLATION"


def test_adversarial_secrets_isolation():
    """
    Adversarial Test 5: Candidate code must NEVER be able to read parent application
    secrets, database credentials, or signing keys via os.environ.
    """
    code = """
import os
secret_key = os.environ.get("SECRET_KEY", "NOT_FOUND")
db_url = os.environ.get("DATABASE_URL", "NOT_FOUND")
postgres_pass = os.environ.get("POSTGRES_PASSWORD", "NOT_FOUND")
jwt_secret = os.environ.get("JWT_SECRET", "NOT_FOUND")

print(f"SECRET_KEY:{secret_key}")
print(f"DATABASE_URL:{db_url}")
print(f"POSTGRES_PASSWORD:{postgres_pass}")
"""
    test_cases = [{"input": "", "expected_output": "NOT_CHECKED", "is_hidden": False}]
    res = CodingSandboxRunner.execute_code(code, test_cases, timeout_seconds=2)
    actual = res["results"][0]["actual_output"]

    assert "SECRET_KEY:NOT_FOUND" in actual
    assert "DATABASE_URL:NOT_FOUND" in actual
    assert "POSTGRES_PASSWORD:NOT_FOUND" in actual


def test_hidden_test_cases_privacy(client, coding_question_fixture):
    """
    Hidden test cases must remain private:
    - GET problem details returns only sample test cases.
    - POST submit masks hidden inputs and expected outputs.
    """
    q_id = coding_question_fixture.id

    # 1. Verify problem details endpoint
    prob_res = client.get(f"/api/v1/coding/questions/{q_id}")
    assert prob_res.status_code == 200
    prob_data = prob_res.json()
    assert prob_data["total_test_cases_count"] == 4
    assert len(prob_data["sample_test_cases"]) == 2  # Only the 2 non-hidden test cases!
    for stc in prob_data["sample_test_cases"]:
        assert stc["is_hidden"] is False

    # 2. Submit solution
    valid_code = """
import sys
parts = sys.stdin.read().strip().split()
if len(parts) >= 2:
    print(int(parts[0]) + int(parts[1]))
"""
    sub_res = client.post("/api/v1/coding/submit", json={
        "code": valid_code,
        "question_id": q_id,
        "language": "python"
    })
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    assert sub_data["status"] == "COMPLETED"
    assert sub_data["passed_test_cases"] == 4
    assert sub_data["total_test_cases"] == 4

    # Verify hidden test case results have masked inputs and outputs
    hidden_results = [r for r in sub_data["results"] if r["is_hidden"]]
    assert len(hidden_results) == 2
    for hr in hidden_results:
        assert hr["input"] == "[HIDDEN]"
        assert hr["expected_output"] == "[HIDDEN]"
        assert hr["actual_output"] == "[MATCH]"


def test_execution_rate_limiting(client, coding_question_fixture):
    """
    Excessive code execution requests must be rate-limited with HTTP 429.
    """
    q_id = coding_question_fixture.id
    SandboxRateLimiter.reset()

    # Configure a burst limit
    rate_limited = False
    for i in range(settings.SANDBOX_RATE_LIMIT_PER_MINUTE + 5):
        res = client.post("/api/v1/coding/submit", json={
            "code": "print('hello')",
            "question_id": q_id,
            "language": "python"
        })
        if res.status_code == 429:
            rate_limited = True
            assert "Rate limit exceeded" in res.json()["detail"]
            break

    assert rate_limited is True
    SandboxRateLimiter.reset()


def test_internal_runner_interface_authentication(client):
    """
    The internal runner interface must require X-Runner-Token authentication.
    """
    req_payload = {
        "code": "import sys\nprint('internal-ok')",
        "language": "python",
        "test_cases": [{"input": "", "expected_output": "internal-ok", "is_hidden": False}],
        "timeout_seconds": 2,
        "memory_limit_mb": 128
    }

    # 1. Missing token -> 401 Unauthorized
    res_no_token = client.post("/api/v1/coding/internal/execute", json=req_payload)
    assert res_no_token.status_code == 401

    # 2. Invalid token -> 401 Unauthorized
    res_bad_token = client.post(
        "/api/v1/coding/internal/execute",
        json=req_payload,
        headers={"X-Runner-Token": "wrong-secret-token"}
    )
    assert res_bad_token.status_code == 401

    # 3. Valid token -> 200 OK
    res_valid = client.post(
        "/api/v1/coding/internal/execute",
        json=req_payload,
        headers={"X-Runner-Token": settings.INTERNAL_RUNNER_SECRET}
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["all_passed"] is True
    assert data["passed_test_cases"] == 1


def test_submission_queue_and_history(db, client, coding_question_fixture, test_org):
    """
    Test submission status tracking and history retrieval.
    """
    q_id = coding_question_fixture.id

    # Create real assessment, invitation and attempt
    assess = Assessment(
        org_id=test_org.id,
        title="Coding Assessment",
        status=AssessmentStatus.PUBLISHED,
        total_duration_minutes=60
    )
    db.add(assess)
    db.flush()

    inv = CandidateInvitation(
        assessment_id=assess.id,
        org_id=test_org.id,
        email="candidate.coder@example.com",
        full_name="Coder Candidate",
        invitation_token=f"inv-{uuid.uuid4().hex}",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2)
    )
    db.add(inv)
    db.flush()

    att = Attempt(
        invitation_id=inv.id,
        assessment_id=assess.id,
        candidate_name="Coder Candidate",
        candidate_email="candidate.coder@example.com",
        status=AttemptStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
        server_expiry_at=datetime.now(timezone.utc) + timedelta(minutes=60)
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    attempt_id = att.id

    code_1 = "print('wrong')"
    sub1_res = client.post("/api/v1/coding/submit", json={
        "code": code_1,
        "question_id": q_id,
        "attempt_id": attempt_id,
        "language": "python"
    })
    assert sub1_res.status_code == 201
    sub1_id = sub1_res.json()["submission_id"]

    # Check status endpoint
    status_res = client.get(f"/api/v1/coding/submissions/{sub1_id}")
    assert status_res.status_code == 200
    assert status_res.json()["submission_id"] == sub1_id

    # Submit second attempt (partially correct)
    code_2 = """
import sys
x = sys.stdin.read().strip()
if x == '2 3':
    print(5)
else:
    print(0)
"""
    sub2_res = client.post("/api/v1/coding/submit", json={
        "code": code_2,
        "question_id": q_id,
        "attempt_id": attempt_id,
        "language": "python"
    })
    assert sub2_res.status_code == 201

    # History endpoint
    hist_res = client.get(f"/api/v1/coding/attempts/{attempt_id}/questions/{q_id}/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 2
    assert history[0]["submission_id"] == sub2_res.json()["submission_id"]
    assert history[1]["submission_id"] == sub1_id
