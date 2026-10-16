from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import List, Optional
from datetime import datetime
from app.models.assessment import NavigationMode, AssessmentStatus
from app.schemas.question import QuestionVersionResponse


class AssessmentRuleSchema(BaseModel):
    navigation_mode: NavigationMode = NavigationMode.FREE
    section_wise_breaks: bool = False
    randomize_questions: bool = False
    randomize_options: bool = False
    negative_marking_enabled: bool = True
    negative_marking_formula: str = "(correct * positive_marks) - (wrong * negative_marks)"
    full_screen_enforced: bool = True
    max_tab_switches_allowed: int = 3
    webcam_proctoring_enabled: bool = True
    devtools_block_enabled: bool = True
    copy_paste_blocked: bool = True
    # Safe Exam Browser (SEB) Mode
    seb_required: bool = False
    seb_config_key: Optional[str] = None
    seb_browser_exam_keys: List[str] = []
    seb_allow_quit: bool = True
    seb_quit_url: Optional[str] = None
    seb_quit_password_hash: Optional[str] = None


class SectionQuestionCreate(BaseModel):
    question_id: str
    question_version_id: Optional[str] = None  # If omitted, automatically links latest version at freeze time
    positive_marks: float = 1.0
    negative_marks: float = 0.0
    order_index: int = 0


class SectionQuestionResponse(BaseModel):
    id: str
    section_id: str
    question_id: str
    question_version_id: str
    positive_marks: float
    negative_marks: float
    order_index: int
    question_version: Optional[QuestionVersionResponse] = None

    model_config = ConfigDict(from_attributes=True)


class SectionCreate(BaseModel):
    title: str
    duration_minutes: Optional[int] = None
    order_index: int = 0
    cut_off_marks: float = 0.0
    questions: List[SectionQuestionCreate] = []


class SectionResponse(BaseModel):
    id: str
    assessment_id: str
    title: str
    duration_minutes: Optional[int] = None
    order_index: int
    cut_off_marks: float
    section_questions: List[SectionQuestionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AssessmentCreate(BaseModel):
    org_id: str
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    total_duration_minutes: int = 60
    total_marks: float = 100.0
    passing_percentage: float = 50.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_attempts: int = 1
    result_publication_policy: str = "IMMEDIATE"
    rules: Optional[AssessmentRuleSchema] = None
    sections: List[SectionCreate] = []

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be strictly earlier than end_time")
        if self.passing_percentage < 0 or self.passing_percentage > 100:
            raise ValueError("passing_percentage must be between 0 and 100")
        if self.total_duration_minutes <= 0:
            raise ValueError("total_duration_minutes must be positive")
        return self


class AssessmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    status: Optional[AssessmentStatus] = None
    total_duration_minutes: Optional[int] = None
    total_marks: Optional[float] = None
    passing_percentage: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_attempts: Optional[int] = None
    result_publication_policy: Optional[str] = None
    is_active: Optional[bool] = None
    rules: Optional[AssessmentRuleSchema] = None


class AssessmentScheduleRequest(BaseModel):
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be strictly earlier than end_time")
        return self


class AssessmentDetailResponse(BaseModel):
    id: str
    org_id: str
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    status: AssessmentStatus = AssessmentStatus.DRAFT
    version: int = 1
    total_duration_minutes: int
    total_marks: float = 100.0
    passing_percentage: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_attempts: int = 1
    result_publication_policy: str = "IMMEDIATE"
    is_active: bool
    created_at: datetime
    rules: Optional[AssessmentRuleSchema] = None
    sections: List[SectionResponse] = []

    model_config = ConfigDict(from_attributes=True)
