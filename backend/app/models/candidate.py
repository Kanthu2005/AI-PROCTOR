import enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class CandidateStatus(str, enum.Enum):
    INVITED = "INVITED"
    REGISTERED = "REGISTERED"
    VERIFIED = "VERIFIED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    DISQUALIFIED = "DISQUALIFIED"


class CandidateInvitation(BaseModel):
    __tablename__ = "candidate_invitations"

    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    invitation_token = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.INVITED, nullable=False, index=True)
    
    # Pre-test system check & identity verification
    system_check_passed = Column(Boolean, default=False, nullable=False)
    verified_face_reference = Column(Text, nullable=True)  # Snapshot / embedding for comparison
    verification_data = Column(JSON, default=dict, nullable=False)  # Breakdown of 10 checks & states
    manual_approval_granted = Column(Boolean, default=False, nullable=False)
    manual_approval_by = Column(String(36), nullable=True)
    manual_approval_reason = Column(Text, nullable=True)
    
    assessment = relationship("Assessment", back_populates="invitations")
    attempt = relationship("Attempt", uselist=False, back_populates="invitation", cascade="all, delete-orphan")
