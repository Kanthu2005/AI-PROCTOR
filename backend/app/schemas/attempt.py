from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.attempt import AttemptStatus, RiskLevel, HumanReviewStatus


class AutoSaveItem(BaseModel):
    question_id: str
    question_version_id: str
    section_id: str
    selected_option_ids: List[str] = []
    text_response: Optional[str] = None
    code_response: Optional[str] = None
    language: Optional[str] = None
    time_spent_seconds: int = 0
    is_flagged_for_review: bool = False


class AutoSaveRequest(BaseModel):
    answers: List[AutoSaveItem]
    current_question_id: Optional[str] = None


class AutoSaveResponse(BaseModel):
    success: bool
    saved_count: int
    server_time: datetime
    server_expiry_at: datetime
    remaining_seconds: int
    is_auto_submitted: bool = False
    saved_question_ids: List[str] = []
    submission_receipt: Optional[str] = None


class AttemptStartResponse(BaseModel):
    attempt_id: str
    assessment_id: str
    candidate_name: str
    candidate_email: str
    status: AttemptStatus
    started_at: Optional[datetime] = None
    server_time: datetime
    server_expiry_at: Optional[datetime] = None
    remaining_seconds: int
    rules: Dict[str, Any]
    sections: List[Dict[str, Any]]
    saved_answers: Dict[str, Any] = {}
    current_question_id: Optional[str] = None
    submission_receipt: Optional[str] = None
    assessment_title: Optional[str] = None
    total_marks: Optional[float] = None
    passing_percentage: Optional[float] = None


class SubmitAttemptRequest(BaseModel):
    final_answers: Optional[List[AutoSaveItem]] = None


class SubmitAttemptResponse(BaseModel):
    attempt_id: str
    candidate_name: str
    candidate_email: str
    status: str
    submission_receipt: str
    submission_type: str = "MANUAL"
    submitted_at: datetime
    total_score: float
    total_max_marks: float
    percentage: float
    is_passed: bool
    rank: Optional[int] = None
    percentile: Optional[float] = None
    risk_score: float
    risk_level: str
    total_questions: int = 0
    answered_count: int = 0
    unanswered_count: int = 0
    flagged_count: int = 0


class AttemptResultResponse(BaseModel):
    attempt_id: str
    candidate_name: str
    candidate_email: str
    status: AttemptStatus
    submission_receipt: Optional[str] = None
    submission_type: Optional[str] = None
    total_score: float
    total_max_marks: float
    percentage: float
    is_passed: bool
    rank: Optional[int] = None
    percentile: Optional[float] = None
    risk_score: float
    risk_level: RiskLevel
    human_review_status: HumanReviewStatus
    submitted_at: Optional[datetime] = None
    section_breakdown: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)
