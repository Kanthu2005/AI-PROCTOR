from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, status
from app.services.sandbox_service import CodingSandboxRunner

router = APIRouter(prefix="/sandbox", tags=["Coding Sandbox & Evaluation Engine"])


class CodeRunRequest(BaseModel):
    code: str
    language: str = "python"
    test_cases: List[Dict[str, Any]] = []
    timeout_seconds: int = 3


@router.post("/run", status_code=status.HTTP_200_OK)
def run_code_in_sandbox(request: CodeRunRequest):
    """
    Executes candidate Python code against test cases in an isolated container/subprocess environment.
    """
    results = CodingSandboxRunner.execute_code(
        code=request.code,
        test_cases=request.test_cases,
        language=request.language,
        timeout_seconds=request.timeout_seconds
    )
    return results
