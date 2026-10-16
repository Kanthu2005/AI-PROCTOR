from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class ManualEvaluationRequest(BaseModel):
    marks_awarded: float
    reviewer_comments: Optional[str] = None


class ManualEvaluationResponse(BaseModel):
    attempt_id: str
    question_id: str
    marks_awarded: float
    is_correct: Optional[bool] = None
    reviewer_comments: Optional[str] = None
    is_manually_evaluated: bool = True
    evaluated_at: Optional[datetime] = None
    evaluated_by_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AISuggestScoreResponse(BaseModel):
    question_id: str
    suggested_marks: float
    max_marks: float
    confidence: float
    rationale: str
    requires_human_confirmation: bool = True


class EvaluationResultResponse(BaseModel):
    attempt_id: str
    assessment_id: str
    candidate_name: str
    candidate_email: str
    status: str
    evaluation_status: str
    total_score: float
    total_max_marks: float
    percentage: float
    is_passed: bool
    rank: Optional[int] = None
    percentile: Optional[float] = None
    section_scores: Dict[str, Any] = {}
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
