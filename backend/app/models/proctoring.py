import enum
from sqlalchemy import Column, String, Float, ForeignKey, Enum, JSON, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, utc_now


class EventType(str, enum.Enum):
    # Browser & Environment Events
    TAB_SWITCH = "TAB_SWITCH"
    VISIBILITY_CHANGE = "VISIBILITY_CHANGE"
    FULLSCREEN_EXIT = "FULLSCREEN_EXIT"
    DEVTOOLS_OPEN = "DEVTOOLS_OPEN"
    COPY_PASTE_ATTEMPT = "COPY_PASTE_ATTEMPT"
    
    # Device & Hardware Permissions
    CAMERA_PERMISSION_DENIED = "CAMERA_PERMISSION_DENIED"
    MIC_PERMISSION_DENIED = "MIC_PERMISSION_DENIED"
    DEVICE_CHECK_PASSED = "DEVICE_CHECK_PASSED"
    CAMERA_DISCONNECTED = "CAMERA_DISCONNECTED"
    CAMERA_INTERRUPTED = "CAMERA_INTERRUPTED"
    
    # Connection / Network Lifecycle
    CONNECTION_INTERRUPTED = "CONNECTION_INTERRUPTED"
    CONNECTION_RESTORED = "CONNECTION_RESTORED"

    # Computer Vision / Presence Detection
    FACE_PRESENT = "FACE_PRESENT"
    FACE_MISSING = "FACE_MISSING"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    VOICE_DETECTED = "VOICE_DETECTED"


class IncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProctoringIncident(BaseModel):
    __tablename__ = "proctoring_incidents"

    attempt_id = Column(String(36), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    client_event_id = Column(String(64), nullable=True, index=True)
    event_type = Column(Enum(EventType), nullable=False, index=True)
    severity = Column(Enum(IncidentSeverity), default=IncidentSeverity.LOW, nullable=False)
    risk_points = Column(Float, default=5.0, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    snapshot_data = Column(String(500), nullable=True)  # Snapshot reference/URL/hash
    evidence_ref = Column(String(255), nullable=True)
    is_deduplicated = Column(Boolean, default=False, nullable=False)
    occurred_at = Column(DateTime, default=utc_now, nullable=False)

    attempt = relationship("Attempt", back_populates="incidents")


class ProctorReviewDecision(BaseModel):
    __tablename__ = "proctor_review_decisions"

    attempt_id = Column(String(36), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    decision = Column(String(50), nullable=False)  # VALID, SUSPICIOUS, CONFIRMED_VIOLATION, FALSE_POSITIVE
    comments = Column(Text, nullable=True)
    is_escalated = Column(Boolean, default=False, nullable=False)
    escalated_to_role = Column(String(50), nullable=True)
    escalation_reason = Column(Text, nullable=True)
    risk_score_snapshot = Column(Float, default=0.0, nullable=False)
    rule_version = Column(String(50), default="2026.1-explainable", nullable=False)

    attempt = relationship("Attempt", back_populates="review_decisions")
    reviewer = relationship("User")


class ProctoringEvidenceAccessAudit(BaseModel):
    __tablename__ = "proctoring_evidence_access_audits"

    attempt_id = Column(String(36), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    org_id = Column(String(36), nullable=True, index=True)
    action = Column(String(50), default="EVIDENCE_VIEW", nullable=False)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)

    attempt = relationship("Attempt")
    user = relationship("User")
