import enum
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AttemptStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    TIMED_OUT = "TIMED_OUT"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"
    DISQUALIFIED = "DISQUALIFIED"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HumanReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALID = "VALID"
    SUSPICIOUS = "SUSPICIOUS"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    CONFIRMED_VIOLATION = "CONFIRMED_VIOLATION"


class Attempt(BaseModel):
    __tablename__ = "attempts"

    invitation_id = Column(String(36), ForeignKey("candidate_invitations.id", ondelete="CASCADE"), unique=True, nullable=False)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_email = Column(String(255), nullable=False)
    candidate_name = Column(String(255), nullable=False)

    status = Column(Enum(AttemptStatus), default=AttemptStatus.NOT_STARTED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    # Server-side authoritative clock to prevent client tampering:
    server_expiry_at = Column(DateTime, nullable=True, index=True)
    submitted_at = Column(DateTime, nullable=True)
    submission_receipt = Column(String(64), unique=True, nullable=True, index=True)
    submission_type = Column(String(20), default="MANUAL", nullable=True)  # MANUAL, AUTO_DEADLINE
    last_activity_at = Column(DateTime, nullable=True)
    current_question_id = Column(String(36), nullable=True)

    total_score = Column(Float, default=0.0, nullable=False)
    total_max_marks = Column(Float, default=0.0, nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)
    is_passed = Column(Boolean, default=False, nullable=False)
    
    # Section breakdowns and evaluation lifecycle
    evaluation_status = Column(String(32), default="PENDING", nullable=False, index=True)
    section_scores = Column(JSON, default=dict, nullable=False)

    # Individual result release & Recruiter decision
    is_result_released = Column(Boolean, default=False, nullable=False)
    result_released_at = Column(DateTime, nullable=True)
    result_decision = Column(String(32), nullable=True)  # PASSED, FAILED, SHORTLISTED, REJECTED
    recruiter_feedback = Column(Text, nullable=True)

    # Rankings & Percentiles
    rank = Column(Integer, nullable=True)
    percentile = Column(Float, nullable=True)

    # Dynamic AI Proctoring Risk
    risk_score = Column(Float, default=0.0, nullable=False)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW, nullable=False, index=True)
    human_review_status = Column(Enum(HumanReviewStatus), default=HumanReviewStatus.PENDING, nullable=False, index=True)
    proctor_notes = Column(Text, nullable=True)
    tab_switch_count = Column(Integer, default=0, nullable=False)
    disqualified_reason = Column(String(255), nullable=True)
    risk_history = Column(JSON, default=list, nullable=False)
    is_escalated = Column(Boolean, default=False, nullable=False)
    escalated_to_role = Column(String(50), nullable=True)

    # Safe Exam Browser (SEB) Client Evidence
    seb_verified = Column(Boolean, default=False, nullable=False)
    seb_client_platform = Column(String(50), nullable=True)
    seb_verification_mechanism = Column(String(50), nullable=True)  # CONFIG_KEY_HASH, BEK_REQUEST_HASH, JS_API_SESSION_KEY
    seb_verified_at = Column(DateTime, nullable=True)
    seb_client_user_agent = Column(String(255), nullable=True)

    invitation = relationship("CandidateInvitation", back_populates="attempt")
    assessment = relationship("Assessment", back_populates="attempts")
    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    incidents = relationship("ProctoringIncident", back_populates="attempt", cascade="all, delete-orphan")
    review_decisions = relationship("ProctorReviewDecision", back_populates="attempt", cascade="all, delete-orphan", order_by="ProctorReviewDecision.created_at.desc()")


class AttemptAnswer(BaseModel):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answer_question"),
    )

    attempt_id = Column(String(36), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_version_id = Column(String(36), ForeignKey("question_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(String(36), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True)

    selected_option_ids = Column(JSON, default=list, nullable=False)
    text_response = Column(Text, nullable=True)
    code_response = Column(Text, nullable=True)
    code_drafts = Column(JSON, default=dict, nullable=False)
    language = Column(String(50), nullable=True)

    is_correct = Column(Boolean, nullable=True)
    marks_awarded = Column(Float, default=0.0, nullable=False)
    execution_result = Column(JSON, default=dict, nullable=False)
    time_spent_seconds = Column(Integer, default=0, nullable=False)
    is_flagged_for_review = Column(Boolean, default=False, nullable=False)

    # Manual descriptive evaluation & comments
    reviewer_comments = Column(Text, nullable=True)
    evaluated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    is_manually_evaluated = Column(Boolean, default=False, nullable=False)

    # Optional AI-suggested descriptive evaluation (requires human confirmation)
    ai_suggested_marks = Column(Float, nullable=True)
    ai_suggestion_rationale = Column(Text, nullable=True)
    ai_suggestion_confidence = Column(Float, nullable=True)

    attempt = relationship("Attempt", back_populates="answers")
    evaluator = relationship("User", foreign_keys=[evaluated_by_id])
