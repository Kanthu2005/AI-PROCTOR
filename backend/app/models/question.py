import enum
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class QuestionType(str, enum.Enum):
    MCQ_SINGLE = "MCQ_SINGLE"
    MCQ_MULTIPLE = "MCQ_MULTIPLE"
    TRUE_FALSE = "TRUE_FALSE"
    FILL_IN_BLANK = "FILL_IN_BLANK"
    SHORT_ANSWER = "SHORT_ANSWER"
    DESCRIPTIVE = "DESCRIPTIVE"
    SQL = "SQL"
    CODING = "CODING"


class ReviewStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"


class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Question(BaseModel):
    __tablename__ = "questions"

    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    question_type = Column(Enum(QuestionType), nullable=False, index=True)
    current_version_number = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    organization = relationship("Organization", back_populates="questions")
    versions = relationship("QuestionVersion", back_populates="question", cascade="all, delete-orphan", order_by="desc(QuestionVersion.version_number)")

    @property
    def latest_version(self):
        return self.versions[0] if self.versions else None


class QuestionVersion(BaseModel):
    __tablename__ = "question_versions"

    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM, nullable=False)
    
    default_positive_marks = Column(Float, default=1.0, nullable=False)
    default_negative_marks = Column(Float, default=0.0, nullable=False)
    
    tags = Column(JSON, default=list, nullable=False)
    topic = Column(String(100), default="General", nullable=True, index=True)
    explanation = Column(Text, nullable=True)
    options = Column(JSON, default=list, nullable=False)  # [{id, text, is_correct, explanation}]
    coding_details = Column(JSON, default=dict, nullable=False)  # {starter_code, language, test_cases}
    sql_details = Column(JSON, default=dict, nullable=False)  # {schema_sql, solution_sql, test_queries}
    
    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.APPROVED, nullable=False, index=True)
    is_published = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    question = relationship("Question", back_populates="versions")
    author = relationship("User", back_populates="authored_questions")
    section_links = relationship("SectionQuestion", back_populates="question_version")
