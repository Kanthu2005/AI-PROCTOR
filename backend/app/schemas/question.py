from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.question import QuestionType, DifficultyLevel, ReviewStatus


class OptionSchema(BaseModel):
    id: str
    text: str
    is_correct: bool = False
    explanation: Optional[str] = None


class TestCaseSchema(BaseModel):
    input: str
    expected_output: str
    is_hidden: bool = False
    time_limit_ms: int = 2000
    memory_limit_mb: int = 128


class CodingDetailsSchema(BaseModel):
    starter_code: str = ""
    language: str = "python"
    test_cases: List[TestCaseSchema] = []


class SQLDetailsSchema(BaseModel):
    schema_sql: str = ""
    solution_sql: str = ""
    test_queries: List[str] = []


class QuestionCreate(BaseModel):
    org_id: str
    title: str
    description: Optional[str] = ""
    question_type: QuestionType
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    default_positive_marks: float = 1.0
    default_negative_marks: float = 0.0
    tags: List[str] = []
    topic: Optional[str] = "General"
    explanation: Optional[str] = None
    options: List[OptionSchema] = []
    coding_details: Optional[CodingDetailsSchema] = None
    sql_details: Optional[SQLDetailsSchema] = None
    review_status: ReviewStatus = ReviewStatus.DRAFT
    is_published: bool = True

    @model_validator(mode="after")
    def validate_question_data(self):
        q_type = self.question_type
        if q_type == QuestionType.MCQ_SINGLE:
            correct_count = sum(1 for o in self.options if o.is_correct)
            if self.options and len(self.options) >= 2 and correct_count != 1:
                raise ValueError(f"MCQ_SINGLE must have exactly 1 correct option, found {correct_count}")
            elif self.options and correct_count > 1:
                raise ValueError(f"MCQ_SINGLE cannot have more than 1 correct option, found {correct_count}")
        elif q_type == QuestionType.MCQ_MULTIPLE:
            if self.options and len(self.options) >= 2:
                correct_count = sum(1 for o in self.options if o.is_correct)
                if correct_count < 1:
                    raise ValueError("MCQ_MULTIPLE must have at least 1 correct option")
        elif q_type == QuestionType.TRUE_FALSE:
            if not self.options or len(self.options) != 2:
                # Auto-create True/False options if empty
                if not self.options:
                    self.options = [
                        OptionSchema(id="true", text="True", is_correct=True),
                        OptionSchema(id="false", text="False", is_correct=False)
                    ]
            correct_count = sum(1 for o in self.options if o.is_correct)
            if correct_count != 1:
                raise ValueError("TRUE_FALSE question must have exactly 1 correct answer (True or False)")
        elif q_type == QuestionType.FILL_IN_BLANK:
            if self.options:
                correct_count = sum(1 for o in self.options if o.is_correct)
                if correct_count < 1 and not self.explanation:
                    raise ValueError("FILL_IN_BLANK must have at least 1 accepted answer or explanation")
        elif q_type == QuestionType.CODING:
            if not self.coding_details:
                self.coding_details = CodingDetailsSchema()
        elif q_type == QuestionType.SQL:
            if not self.sql_details:
                self.sql_details = SQLDetailsSchema()
        return self


class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    default_positive_marks: Optional[float] = None
    default_negative_marks: Optional[float] = None
    tags: Optional[List[str]] = None
    topic: Optional[str] = None
    explanation: Optional[str] = None
    options: Optional[List[OptionSchema]] = None
    coding_details: Optional[CodingDetailsSchema] = None
    sql_details: Optional[SQLDetailsSchema] = None
    review_status: Optional[ReviewStatus] = None
    is_published: Optional[bool] = None


class QuestionReviewRequest(BaseModel):
    review_status: ReviewStatus
    reviewer_notes: Optional[str] = None


class QuestionVersionResponse(BaseModel):
    id: str
    question_id: str
    version_number: int
    title: str
    description: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    default_positive_marks: float
    default_negative_marks: float
    tags: List[str]
    topic: Optional[str] = "General"
    explanation: Optional[str] = None
    options: List[Dict[str, Any]]
    coding_details: Dict[str, Any]
    sql_details: Dict[str, Any]
    review_status: ReviewStatus = ReviewStatus.APPROVED
    is_published: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionResponse(BaseModel):
    id: str
    org_id: str
    question_type: QuestionType
    current_version_number: int
    is_active: bool
    created_at: datetime
    current_version: Optional[QuestionVersionResponse] = None
    all_versions: Optional[List[QuestionVersionResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedQuestionResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
