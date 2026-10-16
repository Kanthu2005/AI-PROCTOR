from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class CandidateRankItem(BaseModel):
    attempt_id: str
    candidate_name: str
    candidate_email: str
    score: float
    percentage: float
    is_passed: bool
    rank: int
    percentile: float
    time_taken_seconds: int
    accuracy_percentage: float
    risk_level: str
    submitted_at: Optional[datetime] = None


class QuestionAnalyticsItem(BaseModel):
    question_id: str
    title: str
    question_type: str
    total_attempts: int
    correct_attempts: int
    pass_rate_percentage: float
    avg_time_spent_seconds: float
    discrimination_index: float  # Difference in accuracy between top 27% and bottom 27%


class AssessmentAnalyticsResponse(BaseModel):
    assessment_id: str
    assessment_title: str
    total_candidates_invited: int
    total_attempts_started: int
    total_completed: int
    total_passed: int
    overall_pass_percentage: float
    average_score: float
    median_score: float
    highest_score: float
    lowest_score: float
    leaderboard: List[CandidateRankItem]
    question_analytics: List[QuestionAnalyticsItem]
    score_distribution: Dict[str, int] = {}
