from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.coding import (
    CodingProblemDetail, CodeSubmissionCreate, CodeSubmissionResponse,
    InternalRunnerExecutionRequest, InternalRunnerExecutionResponse
)
from app.services.coding_execution_service import CodingExecutionService
from app.services.sandbox_service import CodingSandboxRunner
from app.config import settings

router = APIRouter(prefix="/coding", tags=["Coding Assessment & Sandbox Execution Service"])


@router.get("/questions/{question_id}", response_model=CodingProblemDetail)
def get_coding_problem(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Candidate & Recruiter Coding Problem View:
    - Problem description, constraints, input and output formats
    - Sample test cases ONLY (hidden test cases are strictly stripped)
    """
    return CodingExecutionService.get_coding_problem_details(db, question_id)


@router.post("/submit", response_model=CodeSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_code_for_evaluation(
    req: CodeSubmissionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit candidate code for automated sandbox evaluation:
    - Rate-limited per candidate/client IP
    - Enqueues and executes in isolated security boundary
    - Enforces CPU, memory, time, and output bounds
    - Automatically grades against public & hidden test cases
    - Keeps hidden test inputs & outputs private
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return CodingExecutionService.create_and_execute_submission(
        db=db,
        code=req.code,
        question_id=req.question_id,
        attempt_id=req.attempt_id,
        language=req.language,
        client_ip=client_ip
    )


@router.get("/submissions/{submission_id}", response_model=CodeSubmissionResponse)
def get_submission_status(
    submission_id: str,
    db: Session = Depends(get_db)
):
    """
    Check submission status, execution time, and safe test results.
    """
    return CodingExecutionService.get_submission_status(db, submission_id)


@router.get("/attempts/{attempt_id}/questions/{question_id}/history", response_model=List[CodeSubmissionResponse])
def get_submission_history(
    attempt_id: str,
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full submission history and failure messages for a candidate's attempt question.
    """
    return CodingExecutionService.get_submission_history(db, attempt_id, question_id)


@router.post("/internal/execute", response_model=InternalRunnerExecutionResponse)
def internal_runner_execute(
    req: InternalRunnerExecutionRequest,
    x_runner_token: Optional[str] = Header(None)
):
    """
    Authenticated internal runner interface:
    - Authenticates caller using X-Runner-Token
    - Executes Python code in disposable, hardened sandbox
    - Never executes inside the main server process
    """
    if not CodingSandboxRunner.authenticate_runner_token(x_runner_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing internal runner authentication token."
        )

    res = CodingSandboxRunner.execute_code(
        code=req.code,
        test_cases=req.test_cases,
        language=req.language,
        timeout_seconds=req.timeout_seconds,
        memory_limit_mb=req.memory_limit_mb
    )
    return InternalRunnerExecutionResponse(**res)
