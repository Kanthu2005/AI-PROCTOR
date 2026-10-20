import html
from typing import Optional, Dict, Any


def render_exam_invitation_subject(assessment_title: str, is_reminder: bool = False) -> str:
    """Renders the standard email subject line."""
    prefix = "Reminder: " if is_reminder else ""
    # Strip any newlines in subject to prevent header injection
    safe_title = "".join(assessment_title.splitlines()).strip()
    return f"{prefix}Exam Invitation: {safe_title} — ProctorAI"


def render_exam_invitation_text(context: Dict[str, Any], is_reminder: bool = False) -> str:
    """Renders the standard plain-text email body matching requirement specifications."""
    candidate_name = context.get("candidate_name", "Candidate")
    assessment_title = context.get("assessment_title", "Online Assessment")
    assessment_description = context.get("assessment_description", "Standard assessment evaluation")
    duration = context.get("duration", "60 minutes")
    start_datetime = context.get("start_datetime", "Available upon invitation")
    end_datetime = context.get("end_datetime", "Available until expiration")
    total_marks = context.get("total_marks", "100")
    passing_marks = context.get("passing_marks", "50")
    exam_instructions = context.get("exam_instructions", "Follow all proctoring guidelines during the test.")
    secure_exam_link = context.get("secure_exam_link", "")
    recruiter_name = context.get("recruiter_name", "Assessment Coordinator")
    recruiter_email = context.get("recruiter_email", "support@proctorai.live")
    organization_name = context.get("organization_name", "ProctorAI Assessment Platform")

    reminder_prefix = ""
    if is_reminder:
        reminder_prefix = "[REMINDER] This is a gentle reminder that your exam access window is open.\n\n"

    return f"""Hello {candidate_name},

{reminder_prefix}You have been invited to take an online assessment through ProctorAI.

Exam Details
- Assessment: {assessment_title}
- Description: {assessment_description}
- Duration: {duration}
- Scheduled Start: {start_datetime}
- Scheduled End: {end_datetime}
- Total Marks: {total_marks}
- Passing Marks: {passing_marks}
- Instructions: {exam_instructions}

How to Attend
1. Click the secure exam link below.
2. Sign in or verify your invitation as required.
3. Complete the device and browser checks.
4. Read the exam instructions carefully and start within the permitted time window.
5. Submit your answers before the timer expires.

Start or View Exam
{secure_exam_link}

Please keep your invitation link private. Do not share it with other candidates.

If the exam has a scheduled time, the link should allow the candidate to access the exam only during the permitted window, according to the assessment settings.

If you have questions about the assessment, please contact {recruiter_name} at {recruiter_email}.

Best regards,
{recruiter_name}
{organization_name}
ProctorAI Assessment Platform

*This is an automated assessment invitation. Please do not reply if this inbox is not monitored.*
"""


def render_exam_invitation_html(context: Dict[str, Any], is_reminder: bool = False) -> str:
    """
    Renders a responsive, brand-aligned HTML invitation email with safely escaped dynamic values.
    """
    # Safely escape all user & database values to prevent HTML injection / XSS
    candidate_name = html.escape(str(context.get("candidate_name") or "Candidate"))
    assessment_title = html.escape(str(context.get("assessment_title") or "Online Assessment"))
    assessment_description = html.escape(str(context.get("assessment_description") or "Standard assessment evaluation"))
    duration = html.escape(str(context.get("duration") or "60 minutes"))
    start_datetime = html.escape(str(context.get("start_datetime") or "Available upon receipt"))
    end_datetime = html.escape(str(context.get("end_datetime") or "Until expiration date"))
    total_marks = html.escape(str(context.get("total_marks") or "100"))
    passing_marks = html.escape(str(context.get("passing_marks") or "50"))
    exam_instructions = html.escape(str(context.get("exam_instructions") or "Follow all proctoring guidelines during the test."))
    raw_link = str(context.get("secure_exam_link") or "#")
    secure_exam_link = html.escape(raw_link)
    recruiter_name = html.escape(str(context.get("recruiter_name") or "Assessment Coordinator"))
    recruiter_email = html.escape(str(context.get("recruiter_email") or "support@proctorai.live"))
    organization_name = html.escape(str(context.get("organization_name") or "ProctorAI Organization"))

    reminder_banner = ""
    if is_reminder:
        reminder_banner = """
        <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px;">
            <div style="font-weight: 700; color: #92400e; font-size: 14px; margin-bottom: 4px;">⏰ Friendly Exam Reminder</div>
            <div style="font-size: 13px; color: #78350f; line-height: 1.5;">
                This is a follow-up reminder regarding your online assessment. Please complete your system checks and start your exam before the window expires.
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exam Invitation: {assessment_title} — ProctorAI</title>
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; -webkit-font-smoothing: antialiased;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f1f5f9; padding: 32px 16px;">
        <tr>
            <td align="center">
                <!-- Main Container -->
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 620px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04); border: 1px solid #e2e8f0;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0b1329 0%, #1e293b 100%); padding: 32px 36px; text-align: left; border-bottom: 3px solid #2563eb;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td>
                                        <div style="display: inline-block; background-color: #2563eb; color: #ffffff; font-weight: 800; font-size: 16px; width: 36px; height: 36px; line-height: 36px; text-align: center; border-radius: 10px; margin-right: 12px; vertical-align: middle;">
                                            🛡️
                                        </div>
                                        <span style="font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; vertical-align: middle;">
                                            Proctor<span style="color: #60a5fa;">AI</span>
                                        </span>
                                    </td>
                                    <td align="right">
                                        <span style="background-color: rgba(37, 99, 235, 0.2); color: #93c5fd; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 6px 12px; border-radius: 9999px; border: 1px solid rgba(147, 197, 253, 0.3);">
                                            Secure Assessment
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 36px 36px 28px 36px;">
                            {reminder_banner}

                            <h1 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 0 0 16px 0; line-height: 1.3;">
                                Hello {candidate_name},
                            </h1>
                            <p style="font-size: 15px; line-height: 1.6; color: #334155; margin: 0 0 24px 0;">
                                You have been invited to take an online assessment through <strong>ProctorAI</strong>.
                            </p>

                            <!-- Exam Details Card -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px 24px; margin-bottom: 28px;">
                                <div style="font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 14px; display: flex; align-items: center;">
                                    📋 Exam Details
                                </div>
                                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="font-size: 14px; line-height: 1.8;">
                                    <tr>
                                        <td style="color: #64748b; width: 140px; padding: 4px 0; vertical-align: top;"><strong>Assessment:</strong></td>
                                        <td style="color: #0f172a; font-weight: 600; padding: 4px 0;">{assessment_title}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #64748b; padding: 4px 0; vertical-align: top;"><strong>Description:</strong></td>
                                        <td style="color: #334155; padding: 4px 0;">{assessment_description}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #64748b; padding: 4px 0;"><strong>Duration:</strong></td>
                                        <td style="color: #0f172a; font-weight: 600; padding: 4px 0;">{duration}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #64748b; padding: 4px 0;"><strong>Scheduled Start:</strong></td>
                                        <td style="color: #334155; padding: 4px 0;">{start_datetime}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #64748b; padding: 4px 0;"><strong>Scheduled End:</strong></td>
                                        <td style="color: #334155; padding: 4px 0;">{end_datetime}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #64748b; padding: 4px 0;"><strong>Total Marks:</strong></td>
                                        <td style="color: #0f172a; font-weight: 600; padding: 4px 0;">{total_marks}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #64748b; padding: 4px 0;"><strong>Passing Marks:</strong></td>
                                        <td style="color: #059669; font-weight: 600; padding: 4px 0;">{passing_marks}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #64748b; padding: 4px 0; vertical-align: top;"><strong>Instructions:</strong></td>
                                        <td style="color: #334155; padding: 4px 0;">{exam_instructions}</td>
                                    </tr>
                                </table>
                            </div>

                            <!-- How to Attend -->
                            <div style="margin-bottom: 30px;">
                                <div style="font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 12px;">
                                    🚀 How to Attend
                                </div>
                                <ol style="margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.7; color: #334155;">
                                    <li style="margin-bottom: 6px;">Click the secure exam link below.</li>
                                    <li style="margin-bottom: 6px;">Sign in or verify your invitation as required.</li>
                                    <li style="margin-bottom: 6px;">Complete the device and browser checks (camera, microphone, full screen).</li>
                                    <li style="margin-bottom: 6px;">Read the exam instructions carefully and start within the permitted time window.</li>
                                    <li style="margin-bottom: 6px;">Submit your answers before the timer expires.</li>
                                </ol>
                            </div>

                            <!-- Start Button Call to Action -->
                            <div style="text-align: center; margin: 32px 0 28px 0;">
                                <a href="{secure_exam_link}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background-color: #2563eb; color: #ffffff; font-size: 16px; font-weight: 700; text-decoration: none; padding: 14px 36px; border-radius: 10px; box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.39); letter-spacing: 0.2px;">
                                    Start or View Exam &rarr;
                                </a>
                            </div>

                            <!-- Raw Link Fallback -->
                            <div style="background-color: #f1f5f9; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px; word-break: break-all;">
                                <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px; font-weight: 600;">Direct Link:</span>
                                <a href="{secure_exam_link}" target="_blank" rel="noopener noreferrer" style="font-size: 12px; color: #2563eb; text-decoration: underline;">
                                    {secure_exam_link}
                                </a>
                            </div>

                            <!-- Security Notice -->
                            <div style="border-left: 4px solid #3b82f6; background-color: #eff6ff; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
                                <p style="font-size: 13px; color: #1e40af; margin: 0 0 6px 0; line-height: 1.5;">
                                    🔒 <strong>Private Access Notice:</strong> Please keep your invitation link private. Do not share it with other candidates.
                                </p>
                                <p style="font-size: 13px; color: #1e40af; margin: 0; line-height: 1.5;">
                                    If the exam has a scheduled time, the link should allow the candidate to access the exam only during the permitted window, according to the assessment settings.
                                </p>
                            </div>

                            <!-- Recruiter Contact -->
                            <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 20px 0;">
                                If you have questions about the assessment, please contact <strong>{recruiter_name}</strong> at <a href="mailto:{recruiter_email}" style="color: #2563eb; text-decoration: none;">{recruiter_email}</a>.
                            </p>

                            <!-- Signoff -->
                            <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; font-size: 14px; line-height: 1.6; color: #334155;">
                                Best regards,<br>
                                <strong>{recruiter_name}</strong><br>
                                {organization_name}<br>
                                <span style="color: #64748b; font-size: 13px;">ProctorAI Assessment Platform</span>
                            </div>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 24px 36px; text-align: center;">
                            <p style="font-size: 12px; line-height: 1.5; color: #94a3b8; margin: 0 0 8px 0;">
                                <em>This is an automated assessment invitation. Please do not reply if this inbox is not monitored.</em>
                            </p>
                            <p style="font-size: 11px; color: #cbd5e1; margin: 0;">
                                &copy; 2026 ProctorAI Platform. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
