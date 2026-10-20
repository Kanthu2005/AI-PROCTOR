import abc
import email.utils
import logging
import smtplib
import time
import uuid
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger("proctorai.email.provider")


@dataclass
class EmailSendResult:
    success: bool
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    status_code: Optional[int] = None


class BaseEmailProvider(abc.ABC):
    """
    Abstract base provider defining real transactional email delivery interface.
    """
    @abc.abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> EmailSendResult:
        """Sends an email and returns the structured provider response."""
        pass


class ResendEmailProvider(BaseEmailProvider):
    """
    Provider implementation for Resend transactional email API (https://resend.com).
    Sends requests to https://api.resend.com/emails.
    """
    API_URL = "https://api.resend.com/emails"

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 10.0):
        self.api_key = api_key or settings.RESEND_API_KEY
        self.timeout = timeout_seconds

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> EmailSendResult:
        start_time = time.time()
        
        if not self.api_key:
            err = "RESEND_API_KEY is not configured in environment"
            logger.error("Resend provider error: %s", err)
            return EmailSendResult(
                success=False,
                provider="resend",
                error=err,
                duration_ms=int((time.time() - start_time) * 1000)
            )

        resolved_from_name = from_name or settings.EMAIL_FROM_NAME
        resolved_from_address = from_email or settings.EMAIL_FROM_ADDRESS
        sender_header = f"{resolved_from_name} <{resolved_from_address}>"

        payload: Dict[str, Any] = {
            "from": sender_header,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
            "text": text_body
        }
        if reply_to:
            payload["reply_to"] = reply_to

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ProctorAI-Assessment-Platform/2026.1"
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.API_URL, json=payload, headers=headers)
                duration_ms = int((time.time() - start_time) * 1000)

                if resp.status_code in (200, 201):
                    data = resp.json()
                    message_id = data.get("id") or str(uuid.uuid4())
                    logger.info(
                        "Resend accepted message for recipient %s [id=%s, duration=%dms]",
                        to_email.split('@')[0] + "@***",
                        message_id,
                        duration_ms
                    )
                    return EmailSendResult(
                        success=True,
                        provider="resend",
                        message_id=message_id,
                        status_code=resp.status_code,
                        duration_ms=duration_ms
                    )
                else:
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("message") or str(err_json)
                    except Exception:
                        err_msg = resp.text or f"HTTP {resp.status_code}"
                    logger.warning(
                        "Resend rejected email for recipient [status=%d]: %s",
                        resp.status_code,
                        err_msg
                    )
                    return EmailSendResult(
                        success=False,
                        provider="resend",
                        error=f"Resend API error ({resp.status_code}): {err_msg}",
                        status_code=resp.status_code,
                        duration_ms=duration_ms
                    )

        except httpx.RequestError as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            err_msg = f"Network communication error connecting to Resend: {str(exc)}"
            logger.error(err_msg)
            return EmailSendResult(
                success=False,
                provider="resend",
                error=err_msg,
                duration_ms=duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            err_msg = f"Unexpected error during Resend send: {str(exc)}"
            logger.error(err_msg, exc_info=True)
            return EmailSendResult(
                success=False,
                provider="resend",
                error=err_msg,
                duration_ms=duration_ms
            )


class SMTPEmailProvider(BaseEmailProvider):
    """
    Standard SMTP Provider with SSL/TLS and STARTTLS support.
    Compatible with AWS SES SMTP, SendGrid SMTP, Gmail SMTP, and custom mail relays.
    """
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
        timeout_seconds: float = 15.0
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user if user is not None else settings.SMTP_USER
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.use_ssl = use_ssl if use_ssl is not None else settings.SMTP_USE_SSL
        self.timeout = timeout_seconds

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> EmailSendResult:
        start_time = time.time()
        msg_id = email.utils.make_msgid(domain="proctorai.live")

        resolved_from_name = from_name or settings.EMAIL_FROM_NAME
        resolved_from_address = from_email or settings.EMAIL_FROM_ADDRESS

        # Create multi-part alternative message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = email.utils.formataddr((resolved_from_name, resolved_from_address))
        msg["To"] = to_email
        msg["Message-ID"] = msg_id
        msg["Date"] = email.utils.formatdate(localtime=True)
        if reply_to:
            msg["Reply-To"] = reply_to

        # Attach text then html (email clients prioritize the last alternative)
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        server = None
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
                if self.use_tls:
                    server.starttls()

            if self.user and self.password:
                server.login(self.user, self.password)

            server.sendmail(resolved_from_address, [to_email], msg.as_string())
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info("SMTP sent email to recipient [id=%s, duration=%dms]", msg_id, duration_ms)
            return EmailSendResult(
                success=True,
                provider="smtp",
                message_id=msg_id,
                duration_ms=duration_ms
            )
        except smtplib.SMTPException as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            err_msg = f"SMTP protocol error: {str(exc)}"
            logger.warning(err_msg)
            return EmailSendResult(
                success=False,
                provider="smtp",
                error=err_msg,
                duration_ms=duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            err_msg = f"Failed to connect or deliver via SMTP: {str(exc)}"
            logger.error(err_msg, exc_info=True)
            return EmailSendResult(
                success=False,
                provider="smtp",
                error=err_msg,
                duration_ms=duration_ms
            )
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass


class MockEmailProvider(BaseEmailProvider):
    """
    Mock Email Provider for local testing and deterministic automated test verification.
    Stores sent messages in a class-level list for inspection.
    """
    sent_messages: List[Dict[str, Any]] = []
    should_fail: bool = False
    failure_error: str = "Simulated provider failure"

    @classmethod
    def reset(cls):
        cls.sent_messages.clear()
        cls.should_fail = False
        cls.failure_error = "Simulated provider failure"

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> EmailSendResult:
        start_time = time.time()
        
        if self.should_fail:
            return EmailSendResult(
                success=False,
                provider="mock",
                error=self.failure_error,
                duration_ms=int((time.time() - start_time) * 1000)
            )

        msg_id = f"mock_{uuid.uuid4().hex[:16]}"
        entry = {
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "from_email": from_email or settings.EMAIL_FROM_ADDRESS,
            "from_name": from_name or settings.EMAIL_FROM_NAME,
            "reply_to": reply_to,
            "message_id": msg_id,
            "timestamp": time.time()
        }
        self.sent_messages.append(entry)
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info("Mock provider accepted email for %s [id=%s]", to_email, msg_id)
        return EmailSendResult(
            success=True,
            provider="mock",
            message_id=msg_id,
            duration_ms=duration_ms
        )


def get_email_provider(provider_name: Optional[str] = None) -> BaseEmailProvider:
    """
    Factory function returning the configured EmailProvider instance.
    """
    provider_type = (provider_name or settings.EMAIL_PROVIDER or "resend").lower().strip()
    if provider_type == "smtp":
        return SMTPEmailProvider()
    elif provider_type == "mock":
        return MockEmailProvider()
    elif provider_type == "resend":
        return ResendEmailProvider()
    else:
        logger.warning("Unknown provider '%s'; falling back to Resend provider", provider_type)
        return ResendEmailProvider()
