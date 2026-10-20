#!/usr/bin/env python3
"""
ProctorAI Email Dispatch Test Utility
Use this script to verify real email delivery via Resend, SMTP, or Mock providers.

Usage:
  python scripts/test_email_dispatch.py --to candidate@example.com
  python scripts/test_email_dispatch.py --to candidate@example.com --provider smtp
  python scripts/test_email_dispatch.py --to candidate@example.com --provider mock
"""
import argparse
import sys
import os

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.services.email.provider import get_email_provider
from app.services.email.templates import (
    render_exam_invitation_subject,
    render_exam_invitation_html,
    render_exam_invitation_text,
)


def main():
    parser = argparse.ArgumentParser(description="Test real ProctorAI exam invitation delivery")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--name", default="Candidate Test", help="Candidate full name")
    parser.add_argument("--provider", choices=["resend", "smtp", "mock"], default=None, help="Email provider override")
    parser.add_argument("--assessment", default="Senior Python Backend & Cloud Architecture", help="Assessment title")
    args = parser.parse_args()

    provider_name = args.provider or settings.EMAIL_PROVIDER or "resend"
    print(f"============================================================")
    print(f"ProctorAI Real Email Delivery Test")
    print(f"Provider:           {provider_name}")
    print(f"Sender Address:     {settings.EMAIL_FROM_ADDRESS}")
    print(f"Sender Name:        {settings.EMAIL_FROM_NAME}")
    print(f"Recipient:          {args.to} ({args.name})")
    print(f"Assessment:         {args.assessment}")
    print(f"============================================================")

    provider = get_email_provider(provider_name)

    sample_context = {
        "candidate_name": args.name,
        "candidate_email": args.to,
        "assessment_title": args.assessment,
        "assessment_description": "Production technical evaluation testing real email dispatching capabilities",
        "duration": "90 minutes",
        "start_datetime": "Available Immediately",
        "end_datetime": "Valid for 72 hours",
        "total_marks": "100",
        "passing_marks": "60 (60%)",
        "exam_instructions": "Maintain webcam visibility, do not switch tabs, and adhere to all proctoring guidelines.",
        "secure_exam_link": f"{settings.FRONTEND_BASE_URL.rstrip('/')}/#/candidate_exam?token=TEST_VERIFICATION_SAMPLE_TOKEN",
        "recruiter_name": "ProctorAI Recruitment Team",
        "recruiter_email": settings.EMAIL_FROM_ADDRESS,
        "organization_name": "Acme Global Technology Inc.",
    }

    subject = render_exam_invitation_subject(args.assessment)
    html_body = render_exam_invitation_html(sample_context)
    text_body = render_exam_invitation_text(sample_context)

    print("Attempting delivery via provider...")
    result = provider.send_email(
        to_email=args.to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        from_email=settings.EMAIL_FROM_ADDRESS,
        from_name=settings.EMAIL_FROM_NAME,
        reply_to=settings.EMAIL_FROM_ADDRESS
    )

    if result.success:
        print("\nSUCCESS: Email successfully accepted by provider!")
        print(f"Provider:       {result.provider}")
        print(f"Message ID:     {result.message_id}")
        print(f"Duration:       {result.duration_ms} ms")
        if result.status_code:
            print(f"HTTP Status:    {result.status_code}")
    else:
        print("\nFAILURE: Email delivery failed or was rejected by provider.")
        print(f"Provider:       {result.provider}")
        print(f"Error:          {result.error}")
        print(f"Duration:       {result.duration_ms} ms")
        if provider_name == "resend":
            print("\nTroubleshooting Resend:")
            print("1. Verify RESEND_API_KEY is configured in your .env file.")
            print("2. Ensure your sender domain or EMAIL_FROM_ADDRESS is verified in resend.com.")
            print("   Note: For unverified domains, Resend sandbox only permits sending to your account's signup email.")
        elif provider_name == "smtp":
            print("\nTroubleshooting SMTP:")
            print("1. Verify SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD in your .env.")
            print("2. If using Gmail SMTP, generate an App Password with 2FA enabled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
