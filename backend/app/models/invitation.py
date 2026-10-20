import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ExamInvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    OPENED = "OPENED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class DeliveryAttemptType(str, enum.Enum):
    INITIAL = "INITIAL"
    RESEND = "RESEND"
    REMINDER = "REMINDER"


class DeliveryAttemptStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    FAILED = "FAILED"


class ExamInvitation(BaseModel):
    __tablename__ = "exam_invitations"

    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    candidate_invitation_id = Column(String(36), ForeignKey("candidate_invitations.id", ondelete="SET NULL"), nullable=True, index=True)
    
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255), nullable=False)
    invitation_token_hash = Column(String(64), nullable=False, index=True)
    
    status = Column(Enum(ExamInvitationStatus), default=ExamInvitationStatus.PENDING, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    provider_message_id = Column(String(255), nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    assessment = relationship("Assessment", back_populates="exam_invitations")
    candidate_invitation = relationship("CandidateInvitation", foreign_keys=[candidate_invitation_id])
    delivery_attempts = relationship("InvitationDeliveryAttempt", back_populates="invitation", cascade="all, delete-orphan", order_by="InvitationDeliveryAttempt.created_at.desc()")
    creator = relationship("User", foreign_keys=[created_by])
    candidate = relationship("User", foreign_keys=[candidate_id])


class InvitationDeliveryAttempt(BaseModel):
    __tablename__ = "invitation_delivery_attempts"

    invitation_id = Column(String(36), ForeignKey("exam_invitations.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_type = Column(Enum(DeliveryAttemptType), default=DeliveryAttemptType.INITIAL, nullable=False)
    provider = Column(String(50), nullable=False)
    status = Column(Enum(DeliveryAttemptStatus), default=DeliveryAttemptStatus.PENDING, nullable=False)
    provider_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    invitation = relationship("ExamInvitation", back_populates="delivery_attempts")
