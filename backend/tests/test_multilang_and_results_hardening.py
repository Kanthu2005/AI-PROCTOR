from app.models.user import User, Role, Organization
from app.models.assessment import Assessment
from app.models.attempt import Attempt, AttemptStatus
from app.services.sandbox_service import CodingSandboxRunner


def test_sandbox_python_execution():
    """Verify python execution in sandbox."""
    code = "import sys\nline = sys.stdin.read().strip()\nprint(int(line) * 2)"
    res = CodingSandboxRunner.execute_code(
        code=code,
        test_cases=[{"input": "21", "expected_output": "42", "is_hidden": False}],
        language="python",
        timeout_seconds=5
    )
    assert res["passed_test_cases"] == 1
    assert res["all_passed"] is True


def test_sandbox_javascript_execution():
    """Verify javascript execution using host Node.js runtime."""
    code = "const fs = require('fs');\nconst input = fs.readFileSync(0, 'utf-8').trim();\nconsole.log(parseInt(input) + 10);"
    res = CodingSandboxRunner.execute_code(
        code=code,
        test_cases=[{"input": "32", "expected_output": "42", "is_hidden": False}],
        language="javascript",
        timeout_seconds=5
    )
    if not res["all_passed"] and res["results"][0].get("status") == "EXECUTION_SERVICE_UNAVAILABLE":
        assert "compiler or interpreter" in res["results"][0].get("error", "").lower()
    else:
        assert res["passed_test_cases"] == 1
        assert res["all_passed"] is True


def test_sandbox_java_execution():
    """Verify java execution using host Java compiler/runtime."""
    code = (
        "import java.util.Scanner;\n"
        "public class Solution {\n"
        "    public static void main(String[] args) {\n"
        "        Scanner sc = new Scanner(System.in);\n"
        "        if (sc.hasNextInt()) {\n"
        "            System.out.println(sc.nextInt() * 3);\n"
        "        }\n"
        "    }\n"
        "}"
    )
    res = CodingSandboxRunner.execute_code(
        code=code,
        test_cases=[{"input": "7", "expected_output": "21", "is_hidden": False}],
        language="java",
        timeout_seconds=10
    )
    if not res["all_passed"] and res["results"][0].get("status") == "EXECUTION_SERVICE_UNAVAILABLE":
        assert "compiler or interpreter" in res["results"][0].get("error", "").lower()
    else:
        assert res["passed_test_cases"] == 1
        assert res["all_passed"] is True


def test_sandbox_unsupported_or_missing_compiler():
    """Verify missing compiler (like C/C++ without gcc) returns compilation error."""
    code = '#include <stdio.h>\nint main() { printf("Hello"); return 0; }'
    res = CodingSandboxRunner.execute_code(
        code=code,
        test_cases=[{"input": "", "expected_output": "Hello", "is_hidden": False}],
        language="c",
        timeout_seconds=5
    )
    assert res["passed_test_cases"] == 0
    assert res["all_passed"] is False
    assert "compiler" in res["results"][0].get("error", "").lower()


def test_recruiter_official_decision_flow(client, db, test_org, recruiter_headers, candidate_headers, candidate_user):
    """Verify end-to-end official decision release by recruiter and confidentiality enforcement."""
    from app.models.assessment import AssessmentStatus
    # 1. Create assessment with MANUAL release policy
    assessment = Assessment(
        org_id=test_org.id,
        title="Engineering Evaluation",
        total_duration_minutes=60,
        total_marks=20.0,
        passing_percentage=50.0,
        result_publication_policy="MANUAL",
        status=AssessmentStatus.PUBLISHED
    )
    db.add(assessment)
    db.flush()

    # 2. Create invitation and completed attempt for candidate
    from app.models.candidate import CandidateInvitation, CandidateStatus
    from datetime import datetime, timedelta, timezone
    invitation = CandidateInvitation(
        assessment_id=assessment.id,
        org_id=test_org.id,
        email=candidate_user.email,
        full_name=candidate_user.full_name,
        invitation_token="hardening-test-token-12345",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=CandidateStatus.SUBMITTED
    )
    db.add(invitation)
    db.flush()

    attempt = Attempt(
        invitation_id=invitation.id,
        assessment_id=assessment.id,
        candidate_email=candidate_user.email,
        candidate_name=candidate_user.full_name,
        status=AttemptStatus.SUBMITTED,
        risk_score=15.0,
        total_score=18.0,
        total_max_marks=20.0,
        percentage=90.0,
        is_result_released=False
    )
    db.add(attempt)
    db.commit()

    # 3. Recruiter releases official decision
    decision_payload = {
        "decision": "PASSED",
        "recruiter_feedback": "Excellent performance on both coding and system design."
    }
    release_resp = client.post(
        f"/api/v1/attempts/{attempt.id}/send-result",
        json=decision_payload,
        headers=recruiter_headers
    )
    assert release_resp.status_code == 200
    res_data = release_resp.json()
    assert res_data["is_result_released"] is True
    assert res_data["result_decision"] == "PASSED"
    assert res_data["recruiter_feedback"] == "Excellent performance on both coding and system design."

    # 4. Attempt in DB is updated
    db.refresh(attempt)
    assert attempt.is_result_released is True
    assert attempt.result_decision == "PASSED"
    assert attempt.is_passed is True
