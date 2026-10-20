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
    id: Optional[str] = None
    label: Optional[str] = "Test Case"
    input: str = ""
    expected_output: str
    is_hidden: bool = False
    enabled: bool = True
    notes: Optional[str] = None
    time_limit_ms: int = 3000
    memory_limit_mb: int = 128


class CodingDetailsSchema(BaseModel):
    allowed_languages: List[str] = ["python"]
    default_language: str = "python"
    starter_codes: Dict[str, str] = Field(default_factory=dict)
    language_instructions: Dict[str, str] = Field(default_factory=dict)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    examples: Optional[str] = None
    time_limit_seconds: int = 3
    memory_limit_mb: int = 128
    
    # Backwards compatibility fields
    starter_code: Optional[str] = ""
    language: Optional[str] = "python"
    test_cases: List[TestCaseSchema] = []


class SQLDetailsSchema(BaseModel):
    schema_sql: str = ""
    solution_sql: str = ""
    test_queries: List[str] = []


class DescriptiveDetailsSchema(BaseModel):
    evaluation_criteria: Optional[str] = ""
    expected_answer: Optional[str] = ""
    min_words: Optional[int] = 0
    max_words: Optional[int] = 1000
    rubric: Optional[Dict[str, Any]] = None


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
    descriptive_details: Optional[DescriptiveDetailsSchema] = None
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
            if not self.options:
                self.options = [
                    OptionSchema(id="true", text="True", is_correct=True),
                    OptionSchema(id="false", text="False", is_correct=False)
                ]
            if len(self.options) != 2:
                raise ValueError("TRUE_FALSE question must have exactly 2 options (True and False)")
            correct_count = sum(1 for o in self.options if o.is_correct)
            if correct_count != 1:
                raise ValueError("TRUE_FALSE question must have exactly 1 correct answer (True or False)")
        elif q_type == QuestionType.FILL_IN_BLANK:
            if self.options:
                correct_count = sum(1 for o in self.options if o.is_correct)
                if correct_count < 1 and not self.explanation:
                    raise ValueError("FILL_IN_BLANK must have at least 1 accepted answer or explanation")
        elif q_type == QuestionType.DESCRIPTIVE:
            if not self.descriptive_details:
                self.descriptive_details = DescriptiveDetailsSchema()
        elif q_type == QuestionType.CODING:
            if not self.coding_details:
                raise ValueError("CODING questions require coding_details with test cases")
            if not self.coding_details.test_cases:
                raise ValueError("Python CODING questions must have at least 1 test case")
            for idx, tc in enumerate(self.coding_details.test_cases):
                if tc.expected_output is None or str(tc.expected_output).strip() == "":
                    raise ValueError(f"Test case #{idx + 1} must have a non-empty expected_output")
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
    descriptive_details: Optional[DescriptiveDetailsSchema] = None
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
    descriptive_details: Dict[str, Any] = Field(default_factory=dict)
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
