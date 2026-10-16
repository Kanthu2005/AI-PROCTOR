import enum
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class NavigationMode(str, enum.Enum):
    FREE = "FREE"
    FORWARD_ONLY = "FORWARD_ONLY"


class AssessmentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    CLOSED = "CLOSED"


class Assessment(BaseModel):
    __tablename__ = "assessments"

    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.DRAFT, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    total_duration_minutes = Column(Integer, default=60, nullable=False)
    total_marks = Column(Float, default=100.0, nullable=False)
    passing_percentage = Column(Float, default=50.0, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    max_attempts = Column(Integer, default=1, nullable=False)
    result_publication_policy = Column(String(50), default="IMMEDIATE", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    organization = relationship("Organization", back_populates="assessments")
    creator = relationship("User", back_populates="authored_assessments")
    rules = relationship("AssessmentRule", uselist=False, back_populates="assessment", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="assessment", cascade="all, delete-orphan", order_by="Section.order_index")
    invitations = relationship("CandidateInvitation", back_populates="assessment", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentRule(BaseModel):
    __tablename__ = "assessment_rules"

    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), unique=True, nullable=False)
    navigation_mode = Column(Enum(NavigationMode), default=NavigationMode.FREE, nullable=False)
    section_wise_breaks = Column(Boolean, default=False, nullable=False)
    randomize_questions = Column(Boolean, default=False, nullable=False)
    randomize_options = Column(Boolean, default=False, nullable=False)
    negative_marking_enabled = Column(Boolean, default=True, nullable=False)
    negative_marking_formula = Column(String(255), default="(correct * positive_marks) - (wrong * negative_marks)", nullable=False)
    multiple_select_policy = Column(String(50), default="PARTIAL_WITH_PENALTY", nullable=False)  # PARTIAL_WITH_PENALTY, ALL_OR_NOTHING
    
    # Proctoring Rules
    full_screen_enforced = Column(Boolean, default=True, nullable=False)
    max_tab_switches_allowed = Column(Integer, default=3, nullable=False)
    webcam_proctoring_enabled = Column(Boolean, default=True, nullable=False)
    devtools_block_enabled = Column(Boolean, default=True, nullable=False)
    copy_paste_blocked = Column(Boolean, default=True, nullable=False)

    # Safe Exam Browser (SEB) High-Security Mode
    seb_required = Column(Boolean, default=False, nullable=False)
    seb_config_key = Column(String(64), nullable=True)
    seb_browser_exam_keys = Column(JSON, default=list, nullable=False)
    seb_allow_quit = Column(Boolean, default=True, nullable=False)
    seb_quit_url = Column(String(255), nullable=True)
    seb_quit_password_hash = Column(String(128), nullable=True)

    assessment = relationship("Assessment", back_populates="rules")


class Section(BaseModel):
    __tablename__ = "sections"

    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    duration_minutes = Column(Integer, nullable=True)  # Section-specific timer if applicable
    order_index = Column(Integer, default=0, nullable=False)
    cut_off_marks = Column(Float, default=0.0, nullable=False)

    assessment = relationship("Assessment", back_populates="sections")
    section_questions = relationship("SectionQuestion", back_populates="section", cascade="all, delete-orphan", order_by="SectionQuestion.order_index")


class SectionQuestion(BaseModel):
    __tablename__ = "section_questions"

    section_id = Column(String(36), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    # Frozen version id ensures test integrity even when question authors modify the question afterwards!
    question_version_id = Column(String(36), ForeignKey("question_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    positive_marks = Column(Float, default=1.0, nullable=False)
    negative_marks = Column(Float, default=0.0, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    section = relationship("Section", back_populates="section_questions")
    question_version = relationship("QuestionVersion", back_populates="section_links")
