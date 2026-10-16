import json
import logging
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.user import SecurityAuditEvent

logger = logging.getLogger("proctorai.audit")


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        org_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Optional[SecurityAuditEvent]:
        """
        Records a security audit trail event into the audit database table.
        """
        try:
            details_str = None
            if details is not None:
                if isinstance(details, (dict, list)):
                    details_str = json.dumps(details)
                else:
                    details_str = str(details)

            audit_entry = SecurityAuditEvent(
                event_type=event_type,
                user_id=user_id,
                email=email,
                org_id=org_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details_str
            )
            db.add(audit_entry)
            db.commit()
            db.refresh(audit_entry)
            logger.info(f"[AUDIT] {event_type} | User: {user_id or email or 'anonymous'} | Org: {org_id} | Details: {details_str}")
            return audit_entry
        except Exception as e:
            logger.error(f"Failed to record audit event '{event_type}': {e}")
            db.rollback()
            return None
