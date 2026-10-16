from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TestCasePublic(BaseModel):
    test_case_index: int
    input: str
    expected_output: str
    is_hidden: bool = False
    explanation: Optional[str] = None


class CodingProblemDetail(BaseModel):
    question_id: str
    title: str
    description: str
    difficulty: str
    starter_code: Optional[str] = None
    language: str = "python"
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    time_limit_seconds: int = 3
    memory_limit_mb: int = 128
    sample_test_cases: List[Dict[str, Any]] = []
    total_test_cases_count: int = 0


class CodeSubmissionCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000)
    language: str = "python"
    question_id: str
    attempt_id: Optional[str] = None


class TestCaseResult(BaseModel):
    test_case_index: int
    passed: bool
    execution_time_ms: int
    is_hidden: bool
    input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    error: Optional[str] = None


class CodeSubmissionResponse(BaseModel):
    submission_id: str
    attempt_id: Optional[str] = None
    question_id: str
    status: str
    total_test_cases: int
    passed_test_cases: int
    score_awarded: float
    max_marks: float
    execution_time_ms: int
    memory_used_kb: int
    results: List[TestCaseResult] = []
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InternalRunnerExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    test_cases: List[Dict[str, Any]]
    timeout_seconds: int = 3
    memory_limit_mb: int = 128


class InternalRunnerExecutionResponse(BaseModel):
    total_test_cases: int
    passed_test_cases: int
    all_passed: bool
    results: List[Dict[str, Any]]
    error: Optional[str] = None
