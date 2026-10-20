import os
from datetime import datetime, timedelta, timezone
import pytest
from app.config import settings
from app.models.assessment import Assessment
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.invitation import ExamInvitation, ExamInvitationStatus, InvitationDeliveryAttempt
from app.models.user import Organization
from app.services.email.provider import MockEmailProvider
from app.services.email.templates import (
    render_exam_invitation_subject,
    render_exam_invitation_html,
    render_exam_invitation_text,
)


@pytest.fixture(autouse=True)
def setup_mock_email_provider():
    """Ensure email provider is set to mock and reset before each test."""
    original_provider = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "mock"
    MockEmailProvider.reset()
    yield
    settings.EMAIL_PROVIDER = original_provider
    MockEmailProvider.reset()


def create_test_assessment(client, test_org, recruiter_headers, title="DevOps Technical Assessment"):
    resp = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": title,
        "description": "Evaluate cloud infrastructure and DevOps skills",
        "instructions": "No external aids allowed.",
        "total_duration_minutes": 75,
        "total_marks": 100.0,
        "passing_percentage": 60.0
    }, headers=recruiter_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_send_exam_invitations_success(client, test_org, recruiter_headers, db):
    a_id = create_test_assessment(client, test_org, recruiter_headers)

    payload = {
        "candidates": [
            {"email": "alex.dev@example.com", "full_name": "Alex Johnson"},
            {"email": "sam.tester@example.com", "full_name": "Samira Patel"}
        ],
        "expires_in_hours": 48
    }

    # Test both /api/v1/ and /api/ routes
    resp = client.post(f"/api/v1/assessments/{a_id}/invitations", json=payload, headers=recruiter_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_processed"] == 2
    assert data["total_sent"] == 2
    assert data["total_failed"] == 0
    assert len(data["invitations"]) == 2

    # Verify mock provider recorded sent messages
    assert len(MockEmailProvider.sent_messages) == 2
    sent_emails = [m["to"] for m in MockEmailProvider.sent_messages]
    assert "alex.dev@example.com" in sent_emails
    assert "sam.tester@example.com" in sent_emails

    # Verify database records
    inv1 = db.query(ExamInvitation).filter(ExamInvitation.recipient_email == "alex.dev@example.com").first()
    assert inv1 is not None
    assert inv1.status == ExamInvitationStatus.SENT
    assert inv1.provider_message_id is not None
    assert inv1.sent_at is not None
    assert len(inv1.invitation_token_hash) == 64  # SHA-256 hash length

    # Verify delivery attempt logged
    attempts = db.query(InvitationDeliveryAttempt).filter(InvitationDeliveryAttempt.invitation_id == inv1.id).all()
    assert len(attempts) >= 1
    assert attempts[0].status.value == "ACCEPTED"
    assert attempts[0].provider == "mock"


def test_send_exam_invitations_invalid_email(client, test_org, recruiter_headers):
    a_id = create_test_assessment(client, test_org, recruiter_headers)
    payload = {
        "candidates": [
            {"email": "not-a-valid-email", "full_name": "Invalid Candidate"}
        ]
    }
    resp = client.post(f"/api/v1/assessments/{a_id}/invitations", json=payload, headers=recruiter_headers)
    assert resp.status_code == 422


def test_send_exam_invitations_unauthorized_roles(client, test_org, recruiter_headers, author_headers, candidate_headers):
    a_id = create_test_assessment(client, test_org, recruiter_headers)
    payload = {
        "candidates": [{"email": "target@example.com", "full_name": "Target Candidate"}]
    }

    # Question Author cannot invite candidates
    resp_author = client.post(f"/api/v1/assessments/{a_id}/invitations", json=payload, headers=author_headers)
    assert resp_author.status_code == 403

    # Candidate cannot invite candidates
    resp_cand = client.post(f"/api/v1/assessments/{a_id}/invitations", json=payload, headers=candidate_headers)
    assert resp_cand.status_code == 403


def test_cross_organization_tenant_isolation(client, test_org, recruiter_headers, db):
    # Create another organization
    other_org = Organization(name="Other Corp", slug="othercorp", is_active=True)
    db.add(other_org)
    db.commit()

    # Create assessment in other org
    other_assessment = Assessment(
        org_id=other_org.id,
        title="Other Org Confidential Test",
        total_duration_minutes=60,
        total_marks=100.0,
        passing_percentage=50.0
    )
    db.add(other_assessment)
    db.commit()

    # Recruiter belonging to test_org tries to invite to other_assessment
    payload = {
        "candidates": [{"email": "spy@example.com", "full_name": "Infiltrator"}]
    }
    resp = client.post(f"/api/v1/assessments/{other_assessment.id}/invitations", json=payload, headers=recruiter_headers)
    assert resp.status_code == 403
    assert "another organization" in resp.json()["detail"].lower()


def test_email_template_rendering_and_xss_escaping():
    context = {
        "candidate_name": "<script>alert('xss')</script>Bob",
        "assessment_title": "Python & 'Security' <Injection> Test",
        "assessment_description": "Test with <b>HTML</b> & tags",
        "duration": "90 mins",
        "start_datetime": "Monday",
        "end_datetime": "Friday",
        "total_marks": "100",
        "passing_marks": "60",
        "exam_instructions": "Do not cheat <img src=x onerror=alert(1)>",
        "secure_exam_link": "https://proctorai.live/#/candidate_exam?token=TEST_TOKEN_123",
        "recruiter_name": "Recruiter <Boss>",
        "recruiter_email": "recruiter@corp.com",
        "organization_name": "Acme & Sons <Inc>",
    }

    subject = render_exam_invitation_subject(context["assessment_title"])
    assert "Python & 'Security' <Injection> Test" in subject

    html = render_exam_invitation_html(context)
    # Check that raw tags are properly escaped in HTML body
    assert "<script>" not in html
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;Bob" in html
    assert "&lt;Injection&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "https://proctorai.live/#/candidate_exam?token=TEST_TOKEN_123" in html

    text = render_exam_invitation_text(context)
    assert "Hello <script>alert('xss')</script>Bob" in text
    assert "Start or View Exam" in text


def test_email_preview_endpoint(client, test_org, recruiter_headers):
    a_id = create_test_assessment(client, test_org, recruiter_headers, title="Cloud Architect Exam")

    preview_resp = client.post(f"/api/v1/assessments/{a_id}/invitations/preview", json={
        "sample_name": "David Candidate",
        "sample_email": "david@test.com"
    }, headers=recruiter_headers)
    assert preview_resp.status_code == 200
    data = preview_resp.json()
    assert "Exam Invitation: Cloud Architect Exam — ProctorAI" in data["subject"]
    assert "David Candidate" in data["html"]
    assert "Cloud Architect Exam" in data["text"]
    assert "Start or View Exam" in data["text"]


def test_provider_failure_and_retries(client, test_org, recruiter_headers, db):
    a_id = create_test_assessment(client, test_org, recruiter_headers)

    # Configure mock provider to simulate temporary failure
    MockEmailProvider.should_fail = True
    MockEmailProvider.failure_error = "550 5.1.1 Recipient mailbox unavailable"

    payload = {
        "candidates": [{"email": "bounced@example.com", "full_name": "Bounced User"}]
    }
    resp = client.post(f"/api/v1/assessments/{a_id}/invitations", json=payload, headers=recruiter_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_sent"] == 0
    assert data["total_failed"] == 1

    inv = db.query(ExamInvitation).filter(ExamInvitation.recipient_email == "bounced@example.com").first()
    assert inv.status == ExamInvitationStatus.FAILED
    assert "mailbox unavailable" in inv.last_error

    # Verify failure delivery attempt
    attempts = db.query(InvitationDeliveryAttempt).filter(InvitationDeliveryAttempt.invitation_id == inv.id).all()
    assert len(attempts) >= 1
    assert attempts[0].status.value == "FAILED"


def test_resend_and_remind_invitation(client, test_org, recruiter_headers, db):
    a_id = create_test_assessment(client, test_org, recruiter_headers)

    # 1. Initial send
    payload = {
        "candidates": [{"email": "candidate.resend@example.com", "full_name": "Resend Candidate"}]
    }
    send_res = client.post(f"/api/v1/assessments/{a_id}/invitations", json=payload, headers=recruiter_headers)
    assert send_res.status_code == 201
    inv_id = send_res.json()["invitations"][0]["invitation_id"]

    # 2. Resend invitation
    resend_res = client.post(f"/api/v1/invitations/{inv_id}/resend", headers=recruiter_headers)
    assert resend_res.status_code == 200
    assert resend_res.json()["status"] == "SENT"

    # 3. Send reminder
    remind_res = client.post(f"/api/v1/invitations/{inv_id}/remind", headers=recruiter_headers)
    assert remind_res.status_code == 200
    assert remind_res.json()["status"] == "REMINDER_SENT"

    # Verify attempts in db: INITIAL, RESEND, REMINDER
    attempts = db.query(InvitationDeliveryAttempt).filter(
        InvitationDeliveryAttempt.invitation_id == inv_id
    ).order_by(InvitationDeliveryAttempt.created_at.asc()).all()
    assert len(attempts) >= 3
    types = [a.attempt_type.value for a in attempts]
    assert "INITIAL" in types
    assert "RESEND" in types
    assert "REMINDER" in types


def test_public_invitation_token_validation_and_scheduling(client, test_org, recruiter_headers, db):
    a_id = create_test_assessment(client, test_org, recruiter_headers, title="Live Coding Test")

    # Invite candidate to get token
    send_res = client.post(f"/api/v1/assessments/{a_id}/invitations", json={
        "candidates": [{"email": "coder@example.com", "full_name": "Coder Candidate"}]
    }, headers=recruiter_headers)
    assert send_res.status_code == 201
    exam_link = send_res.json()["invitations"][0]["secure_exam_link"]
    raw_token = exam_link.split("token=")[1]

    # Validate token without authentication
    val_res = client.get(f"/api/v1/invitations/validate/{raw_token}")
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["valid"] is True
    assert data["assessment_title"] == "Live Coding Test"
    assert data["candidate_name"] == "Coder Candidate"
    assert data["candidate_email"] == "coder@example.com"
    assert data["schedule_status"] == "AVAILABLE"
    assert data["can_start"] is True

    # Test future schedule window
    assess = db.query(Assessment).filter(Assessment.id == a_id).first()
    assess.start_time = datetime.now(timezone.utc) + timedelta(hours=2)
    db.commit()

    val_future = client.get(f"/api/v1/invitations/validate/{raw_token}")
    assert val_future.json()["schedule_status"] == "UPCOMING"
    assert val_future.json()["can_start"] is False

    # Test past end_time
    assess.start_time = datetime.now(timezone.utc) - timedelta(hours=4)
    assess.end_time = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    val_past = client.get(f"/api/v1/invitations/validate/{raw_token}")
    assert val_past.json()["schedule_status"] == "EXPIRED"
    assert val_past.json()["can_start"] is False


def test_candidate_invitations_list_endpoint(client, test_org, recruiter_headers, candidate_headers, candidate_user):
    a_id = create_test_assessment(client, test_org, recruiter_headers)

    # Invite candidate with candidate_user's email
    client.post(f"/api/v1/assessments/{a_id}/invitations", json={
        "candidates": [{"email": candidate_user.email, "full_name": candidate_user.full_name}]
    }, headers=recruiter_headers)

    # Candidate lists their invitations
    cand_list_resp = client.get("/api/v1/candidate/invitations", headers=candidate_headers)
    assert cand_list_resp.status_code == 200
    items = cand_list_resp.json()
    assert len(items) >= 1
    assert items[0]["recipient_email"] == candidate_user.email.lower()


def test_provider_webhook_delivery_and_opened(client, test_org, recruiter_headers, db):
    a_id = create_test_assessment(client, test_org, recruiter_headers)

    send_res = client.post(f"/api/v1/assessments/{a_id}/invitations", json={
        "candidates": [{"email": "webhook.user@example.com", "full_name": "Webhook Candidate"}]
    }, headers=recruiter_headers)
    inv_data = send_res.json()["invitations"][0]
    provider_msg_id = inv_data["provider_message_id"]

    # 1. Delivered webhook event
    wh_deliv = client.post("/api/v1/invitations/webhook", json={
        "type": "email.delivered",
        "data": {
            "email_id": provider_msg_id
        }
    })
    assert wh_deliv.status_code == 200

    inv = db.query(ExamInvitation).filter(ExamInvitation.provider_message_id == provider_msg_id).first()
    assert inv.status == ExamInvitationStatus.DELIVERED
    assert inv.delivered_at is not None

    # 2. Opened webhook event
    wh_open = client.post("/api/v1/invitations/webhook", json={
        "type": "email.opened",
        "data": {
            "email_id": provider_msg_id
        }
    })
    assert wh_open.status_code == 200

    db.refresh(inv)
    assert inv.status == ExamInvitationStatus.OPENED
    assert inv.opened_at is not None
