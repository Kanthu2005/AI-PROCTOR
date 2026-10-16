import hashlib
import plistlib
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.user import Organization, User, Role
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.models.assessment import Assessment, AssessmentRule, AssessmentStatus, Section, SectionQuestion
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptStatus
from app.services.seb_service import SafeExamBrowserService
from app.utils.security import hash_password, create_access_token


@pytest.fixture
def seb_test_env(db: Session):
    """
    Sets up an organization, recruiter, question, and SEB-enforced assessment.
    """
    org = Organization(name="SEB Secure Org", slug="seb-org", is_active=True)
    db.add(org)
    db.flush()

    recruiter = User(
        email="seb_recruiter@example.com",
        hashed_password=hash_password("Password@123"),
        full_name="SEB Recruiter",
        role=Role.RECRUITER,
        org_id=org.id,
        is_active=True
    )
    db.add(recruiter)
    db.flush()

    # Pre-calculated test keys
    test_config_key = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    windows_bek = "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff"
    macos_bek = "9999888877776666555544443333222211110000ffeeddccbbaa998877665544"

    # Create assessment
    assessment = Assessment(
        org_id=org.id,
        title="High-Security SEB Certified Exam",
        description="Assessment requiring authentic Safe Exam Browser lockdown",
        total_duration_minutes=45,
        total_marks=20.0,
        passing_percentage=60.0,
        status=AssessmentStatus.PUBLISHED,
        created_by_id=recruiter.id
    )
    db.add(assessment)
    db.flush()

    # Create SEB rules
    rule = AssessmentRule(
        assessment_id=assessment.id,
        full_screen_enforced=True,
        seb_required=True,
        seb_config_key=test_config_key,
        seb_browser_exam_keys=[windows_bek, macos_bek],
        seb_allow_quit=True,
        seb_quit_url="http://testserver/api/v1/seb/quit"
    )
    db.add(rule)

    # Add question and section
    q = Question(
        org_id=org.id,
        question_type=QuestionType.MCQ_SINGLE,
        current_version_number=1,
        is_active=True
    )
    db.add(q)
    db.flush()

    qv = QuestionVersion(
        question_id=q.id,
        version_number=1,
        title="What is Safe Exam Browser?",
        description="Select the correct definition",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            {"id": "opt-1", "text": "A lockdown kiosk browser", "is_correct": True},
            {"id": "opt-2", "text": "An ordinary text editor", "is_correct": False}
        ],
        default_positive_marks=20.0,
        default_negative_marks=0.0
    )
    db.add(qv)
    db.flush()

    sec = Section(assessment_id=assessment.id, title="Core Security", order_index=0)
    db.add(sec)
    db.flush()

    sq = SectionQuestion(
        section_id=sec.id,
        question_id=q.id,
        question_version_id=qv.id,
        positive_marks=20.0,
        negative_marks=0.0,
        order_index=0
    )
    db.add(sq)

    # Candidate invitation
    invitation = CandidateInvitation(
        assessment_id=assessment.id,
        org_id=org.id,
        email="candidate_seb@example.com",
        full_name="Secure Candidate",
        invitation_token="SEB-TOKEN-998877",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=CandidateStatus.VERIFIED,
        system_check_passed=True
    )
    db.add(invitation)
    db.commit()

    return {
        "org": org,
        "recruiter": recruiter,
        "assessment": assessment,
        "rule": rule,
        "invitation": invitation,
        "config_key": test_config_key,
        "windows_bek": windows_bek,
        "macos_bek": macos_bek
    }


def test_seb_config_generation_and_plist_structure(client, seb_test_env):
    """
    Verifies that GET /api/v1/seb/assessments/{id}/config.seb generates
    a valid Apple XML Property List conforming to Safe Exam Browser standards.
    """
    assessment_id = seb_test_env["assessment"].id
    res = client.get(f"/api/v1/seb/assessments/{assessment_id}/config.seb")
    assert res.status_code == 200
    assert "application/seb" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]

    # Parse and validate XML plist
    parsed_plist = plistlib.loads(res.content)
    assert isinstance(parsed_plist, dict)
    assert parsed_plist["originatorVersion"] == "SEB_ProctorAI_3.0"
    assert parsed_plist["sendBrowserExamKey"] is True
    assert parsed_plist["browserViewMode"] == 1  # Fullscreen Kiosk
    assert parsed_plist["allowSwitchToApplications"] is False
    assert parsed_plist["enableAltTab"] is False
    assert parsed_plist["hookKeys"] is True
    assert parsed_plist["allowVirtualMachine"] is False
    assert parsed_plist["urlFilterEnable"] is True


def test_candidate_invitation_seb_config_and_launch_urls(client, seb_test_env):
    """
    Verifies candidate-specific .seb config downloads and protocol URLs.
    """
    token = seb_test_env["invitation"].invitation_token
    res = client.get(f"/api/v1/seb/invitations/{token}/config.seb")
    assert res.status_code == 200

    parsed_plist = plistlib.loads(res.content)
    # startURL must contain the candidate's invitation token
    assert token in parsed_plist["startURL"]

    # Verify launch-info endpoint
    launch_res = client.get(f"/api/v1/seb/invitations/{token}/launch-info")
    assert launch_res.status_code == 200
    launch_data = launch_res.json()
    assert launch_data["seb_required"] is True
    assert launch_data["seb_protocol_url"].startswith("seb://") or launch_data["seb_protocol_url"].startswith("sebs://")
    assert "Windows" in launch_data["supported_platforms"]
    assert "macOS" in launch_data["supported_platforms"]
    assert "iOS" in launch_data["supported_platforms"]

    # Verify candidate instructions include SEB metadata
    instr_res = client.get(f"/api/v1/candidates/invitations/{token}/instructions")
    assert instr_res.status_code == 200
    instr_data = instr_res.json()
    assert instr_data["rules"]["seb_required"] is True
    assert instr_data["seb"]["required"] is True
    assert token in instr_data["seb"]["config_url"]


def test_standard_browser_blocked_when_seb_required(client, seb_test_env):
    """
    Verifies that standard browsers (no SEB headers) are strictly blocked with HTTP 403
    and an informative SEB_CLIENT_REQUIRED error code.
    """
    token = seb_test_env["invitation"].invitation_token
    # Standard browser launching without SEB headers
    res = client.post(
        f"/api/v1/attempts/start?invitation_token={token}",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["code"] == "SEB_CLIENT_REQUIRED"
    assert "Safe Exam Browser" in detail["message"]
    assert detail["lockdown_guaranteed"] is False


def test_anti_spoofing_protections(client, seb_test_env):
    """
    Adversarial verification:
    - Attempting to pass ?seb=true or { is_seb: true } must fail.
    - Spoofing User-Agent alone without cryptographic hash must fail.
    - Supplying a random/tampered hash must fail with SEB_HASH_MISMATCH.
    """
    token = seb_test_env["invitation"].invitation_token

    # 1. Query parameter spoofing
    res1 = client.post(
        f"/api/v1/attempts/start?invitation_token={token}&seb=true&is_seb=1",
        headers={"User-Agent": "Chrome/120.0.0"}
    )
    assert res1.status_code == 403
    assert res1.json()["detail"]["code"] == "SEB_CLIENT_REQUIRED"

    # 2. User-Agent spoofing
    res2 = client.post(
        f"/api/v1/attempts/start?invitation_token={token}",
        headers={"User-Agent": "SEB/3.4.0 (Windows NT 10.0)"}
    )
    assert res2.status_code == 403
    assert res2.json()["detail"]["code"] == "SEB_CLIENT_REQUIRED"

    # 3. Tampered Config Key hash
    res3 = client.post(
        f"/api/v1/attempts/start?invitation_token={token}",
        headers={
            "User-Agent": "SEB/3.4.0 (Windows NT 10.0)",
            "X-SafeExamBrowser-ConfigKeyHash": "deadbeefcafebabe0000111122223333444455556666777788889999aaaabbbb"
        }
    )
    assert res3.status_code == 403
    assert res3.json()["detail"]["code"] == "SEB_HASH_MISMATCH"


def test_valid_config_key_hash_allows_full_lifecycle(client, seb_test_env, db: Session):
    """
    Verifies that an authentic Safe Exam Browser client calculating
    X-SafeExamBrowser-ConfigKeyHash = SHA256(request_url + config_key)
    can start, autosave, recover state, and submit the exam.
    """
    token = seb_test_env["invitation"].invitation_token
    config_key = seb_test_env["config_key"]

    start_url = f"http://testserver/api/v1/attempts/start?invitation_token={token}"
    valid_ck_hash = SafeExamBrowserService.compute_request_hash(start_url, config_key)

    # 1. Start Attempt with valid Config Key hash
    start_res = client.post(
        start_url,
        headers={
            "User-Agent": "SEB/3.4.0 (Windows NT 10.0)",
            "X-SafeExamBrowser-ConfigKeyHash": valid_ck_hash
        }
    )
    assert start_res.status_code == 200
    start_data = start_res.json()
    attempt_id = start_data["attempt_id"]
    assert start_data["status"] == "IN_PROGRESS"
    assert len(start_data["sections"]) > 0

    # Verify attempt record in database has verifiable SEB evidence
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    assert attempt.seb_verified is True
    assert attempt.seb_verification_mechanism == "CONFIG_KEY_HASH"
    assert attempt.seb_client_platform == "Windows"
    assert attempt.seb_verified_at is not None

    # 2. Autosave with valid Config Key hash
    autosave_url = f"http://testserver/api/v1/attempts/{attempt_id}/answers/autosave"
    autosave_hash = SafeExamBrowserService.compute_request_hash(autosave_url, config_key)

    save_payload = {
        "answers": [
            {
                "question_id": start_data["sections"][0]["questions"][0]["question_id"],
                "question_version_id": start_data["sections"][0]["questions"][0]["question_version_id"],
                "section_id": start_data["sections"][0]["id"],
                "selected_option_ids": ["opt-1"],
                "time_spent_seconds": 15
            }
        ]
    }
    save_res = client.post(
        autosave_url,
        json=save_payload,
        headers={
            "User-Agent": "SEB/3.4.0 (Windows NT 10.0)",
            "X-SafeExamBrowser-ConfigKeyHash": autosave_hash
        }
    )
    assert save_res.status_code == 200
    assert save_res.json()["success"] is True

    # 3. State recovery
    state_url = f"http://testserver/api/v1/attempts/{attempt_id}/state"
    state_hash = SafeExamBrowserService.compute_request_hash(state_url, config_key)
    state_res = client.get(
        state_url,
        headers={
            "User-Agent": "SEB/3.4.0 (Windows NT 10.0)",
            "X-SafeExamBrowser-ConfigKeyHash": state_hash
        }
    )
    assert state_res.status_code == 200
    assert state_res.json()["status"] == "IN_PROGRESS"

    # 4. Submit Attempt
    submit_url = f"http://testserver/api/v1/attempts/{attempt_id}/submit"
    submit_hash = SafeExamBrowserService.compute_request_hash(submit_url, config_key)
    submit_res = client.post(
        submit_url,
        json={},
        headers={
            "User-Agent": "SEB/3.4.0 (Windows NT 10.0)",
            "X-SafeExamBrowser-ConfigKeyHash": submit_hash
        }
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["status"] == "SUBMITTED"
    assert submit_data["submission_receipt"] is not None
    assert submit_data["is_passed"] is True
    assert submit_data["total_score"] == 20.0


def test_browser_exam_key_multi_platform_verification(client, seb_test_env, db: Session):
    """
    Verifies that the server validates platform-specific Browser Exam Keys (BEKs)
    for Windows and macOS clients via X-SafeExamBrowser-RequestHash.
    """
    assessment_id = seb_test_env["assessment"].id
    org_id = seb_test_env["org"].id
    windows_bek = seb_test_env["windows_bek"]
    macos_bek = seb_test_env["macos_bek"]

    # Create candidate 1 (macOS)
    inv1 = CandidateInvitation(
        assessment_id=assessment_id,
        org_id=org_id,
        email="mac_candidate@example.com",
        full_name="Mac Candidate",
        invitation_token="MAC-SEB-TOKEN-111",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=CandidateStatus.VERIFIED,
        system_check_passed=True
    )
    db.add(inv1)
    db.commit()

    # macOS client uses macOS BEK
    mac_url = f"http://testserver/api/v1/attempts/start?invitation_token={inv1.invitation_token}"
    mac_hash = SafeExamBrowserService.compute_request_hash(mac_url, macos_bek)

    mac_res = client.post(
        mac_url,
        headers={
            "User-Agent": "SEB/3.3.2 (Macintosh; Intel Mac OS X 10_15_7)",
            "X-SafeExamBrowser-RequestHash": mac_hash
        }
    )
    assert mac_res.status_code == 200
    mac_data = mac_res.json()
    assert mac_data["status"] == "IN_PROGRESS"

    attempt1 = db.query(Attempt).filter(Attempt.id == mac_data["attempt_id"]).first()
    assert attempt1.seb_verified is True
    assert attempt1.seb_verification_mechanism == "BEK_REQUEST_HASH"
    assert attempt1.seb_client_platform == "macOS"

    # Create candidate 2 (Windows)
    inv2 = CandidateInvitation(
        assessment_id=assessment_id,
        org_id=org_id,
        email="win_candidate@example.com",
        full_name="Win Candidate",
        invitation_token="WIN-SEB-TOKEN-222",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=CandidateStatus.VERIFIED,
        system_check_passed=True
    )
    db.add(inv2)
    db.commit()

    # Windows client uses Windows BEK
    win_url = f"http://testserver/api/v1/attempts/start?invitation_token={inv2.invitation_token}"
    win_hash = SafeExamBrowserService.compute_request_hash(win_url, windows_bek)

    win_res = client.post(
        win_url,
        headers={
            "User-Agent": "SEB/3.4.0 (Windows NT 10.0; Win64; x64)",
            "X-SafeExamBrowser-RequestHash": win_hash
        }
    )
    assert win_res.status_code == 200
    win_data = win_res.json()

    attempt2 = db.query(Attempt).filter(Attempt.id == win_data["attempt_id"]).first()
    assert attempt2.seb_verified is True
    assert attempt2.seb_verification_mechanism == "BEK_REQUEST_HASH"
    assert attempt2.seb_client_platform == "Windows"


def test_seb_client_diagnostic_endpoint(client, seb_test_env):
    """
    Tests POST /api/v1/seb/verify-client diagnostic endpoint for candidates
    to verify their SEB environment before launching the test.
    """
    token = seb_test_env["invitation"].invitation_token
    config_key = seb_test_env["config_key"]

    test_url = "http://testserver/api/v1/seb/verify-client"

    # 1. Without headers
    diag_res1 = client.post(
        test_url,
        json={"invitation_token": token, "request_url": test_url}
    )
    assert diag_res1.status_code == 200
    diag1 = diag_res1.json()
    assert diag1["is_seb_verified"] is False
    assert diag1["lockdown_guaranteed"] is False
    assert "Safe Exam Browser" in diag1["failure_reason"]

    # 2. With valid Config Key Hash
    diag_hash = SafeExamBrowserService.compute_request_hash(test_url, config_key)
    diag_res2 = client.post(
        test_url,
        json={
            "invitation_token": token,
            "request_url": test_url,
            "seb_config_key_hash": diag_hash,
            "user_agent": "SEB/3.4.0 (Windows NT 10.0)"
        }
    )
    assert diag_res2.status_code == 200
    diag2 = diag_res2.json()
    assert diag2["is_seb_verified"] is True
    assert diag2["lockdown_guaranteed"] is True
    assert diag2["verification_mechanism"] == "CONFIG_KEY_HASH"
    assert diag2["platform_detected"] == "Windows"
    assert diag2["matched_key_type"] == "CONFIG_KEY"


def test_seb_quit_endpoint(client):
    """
    Tests GET /api/v1/seb/quit landing page.
    """
    res = client.get("/api/v1/seb/quit")
    assert res.status_code == 200
    data = res.json()
    assert data["can_quit"] is True
    assert "safely quit" in data["message"].lower()
