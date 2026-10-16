import enum
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SubmissionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"


class CodingSubmission(BaseModel):
    __tablename__ = "coding_submissions"

    attempt_id = Column(String(36), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=True, index=True)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_version_id = Column(String(36), ForeignKey("question_versions.id", ondelete="CASCADE"), nullable=True, index=True)
    candidate_email = Column(String(255), nullable=True, index=True)

    code = Column(Text, nullable=False)
    language = Column(String(50), default="python", nullable=False)

    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.QUEUED, nullable=False, index=True)
    total_test_cases = Column(Integer, default=0, nullable=False)
    passed_test_cases = Column(Integer, default=0, nullable=False)
    score_awarded = Column(Float, default=0.0, nullable=False)
    max_marks = Column(Float, default=0.0, nullable=False)

    execution_time_ms = Column(Integer, default=0, nullable=False)
    memory_used_kb = Column(Integer, default=0, nullable=False)
    results = Column(JSON, default=list, nullable=False)
    error_message = Column(Text, nullable=True)

    attempt = relationship("Attempt")
    question = relationship("Question")
    question_version = relationship("QuestionVersion")
