import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.question import Question, QuestionVersion, QuestionType
from app.models.attempt import Attempt, AttemptAnswer
from app.models.coding import CodingSubmission, SubmissionStatus
from app.schemas.coding import CodingProblemDetail, CodeSubmissionResponse, TestCaseResult
from app.services.sandbox_service import CodingSandboxRunner, SandboxRateLimiter

logger = logging.getLogger("proctorai.coding_service")


class CodingExecutionService:
    @staticmethod
    def get_coding_problem_details(db: Session, question_id: str) -> CodingProblemDetail:
        """
        Retrieves coding problem statement, specifications, constraints, and sample test cases.
        CRITICAL: Hidden test cases are NEVER exposed to candidates.
        """
        q = db.query(Question).filter(Question.id == question_id).first()
        if not q or q.question_type != QuestionType.CODING:
            raise HTTPException(status_code=404, detail="Coding question not found")

        qv = q.latest_version
        if not qv:
            raise HTTPException(status_code=404, detail="Question version not found")

        coding_details = qv.coding_details or {}
        test_cases = coding_details.get("test_cases", [])

        # Filter only public/sample test cases; hide hidden ones
        sample_test_cases = []
        for idx, tc in enumerate(test_cases):
            if not tc.get("is_hidden", False):
                sample_test_cases.append({
                    "test_case_index": idx + 1,
                    "input": str(tc.get("input", "")),
                    "expected_output": str(tc.get("expected_output", "")),
                    "is_hidden": False,
                    "explanation": tc.get("explanation")
                })

        return CodingProblemDetail(
            question_id=q.id,
            title=qv.title,
            description=qv.description,
            difficulty=qv.difficulty.value if qv.difficulty else "MEDIUM",
            starter_code=coding_details.get("starter_code", "# Write your solution below\n"),
            language=coding_details.get("language", "python"),
            input_format=coding_details.get("input_format", "Standard Input (stdin)"),
            output_format=coding_details.get("output_format", "Standard Output (stdout)"),
            constraints=coding_details.get("constraints", "Time limit: 3s | Memory limit: 128MB"),
            time_limit_seconds=coding_details.get("time_limit_seconds", 3),
            memory_limit_mb=coding_details.get("memory_limit_mb", 128),
            sample_test_cases=sample_test_cases,
            total_test_cases_count=len(test_cases)
        )

    @staticmethod
    def create_and_execute_submission(
        db: Session,
        code: str,
        question_id: str,
        attempt_id: Optional[str] = None,
        candidate_email: Optional[str] = None,
        language: str = "python",
        client_ip: Optional[str] = None
    ) -> CodeSubmissionResponse:
        """
        Creates a submission in the queue, enforces rate-limits, runs execution
        through the isolated security boundary, and updates score and results.
        """
        # 1. Rate Limiting Check
        rate_key = candidate_email or client_ip or "anonymous"
        allowed, retry_after = SandboxRateLimiter.check_rate_limit(rate_key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: Too many code execution requests. Please retry in {retry_after} seconds."
            )

        q = db.query(Question).filter(Question.id == question_id).first()
        if not q or q.question_type != QuestionType.CODING:
            raise HTTPException(status_code=404, detail="Coding question not found")

        qv = q.latest_version
        if not qv:
            raise HTTPException(status_code=404, detail="Question version not found")

        coding_details = qv.coding_details or {}
        test_cases = coding_details.get("test_cases", [])
        timeout_seconds = int(coding_details.get("time_limit_seconds", 3))
        memory_limit_mb = int(coding_details.get("memory_limit_mb", 128))

        # Determine question max marks from section if attempt provided
        max_marks = float(qv.default_positive_marks or 10.0)
        valid_attempt_id = None
        if attempt_id:
            from app.models.assessment import SectionQuestion, Section
            att = db.query(Attempt).filter(Attempt.id == attempt_id).first()
            if att:
                valid_attempt_id = att.id
                sq = db.query(SectionQuestion).join(SectionQuestion.section).filter(
                    SectionQuestion.question_id == question_id,
                    Section.assessment_id == att.assessment_id
                ).first()
                if sq:
                    max_marks = float(sq.positive_marks)

        # 2. Create Submission in QUEUED status
        submission = CodingSubmission(
            attempt_id=valid_attempt_id,
            question_id=question_id,
            question_version_id=qv.id,
            candidate_email=candidate_email,
            code=code,
            language=language,
            status=SubmissionStatus.QUEUED,
            total_test_cases=len(test_cases),
            max_marks=max_marks
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        # 3. Transition to PROCESSING
        submission.status = SubmissionStatus.PROCESSING
        db.commit()

        # 4. Execute in isolated sandbox boundary (Never in FastAPI process, no eval/exec)
        exec_res = CodingSandboxRunner.execute_code(
            code=code,
            test_cases=test_cases,
            language=language,
            timeout_seconds=timeout_seconds,
            memory_limit_mb=memory_limit_mb
        )

        passed_count = exec_res.get("passed_test_cases", 0)
        total_tc = exec_res.get("total_test_cases", len(test_cases))
        failure_type = exec_res.get("failure_type")

        # Calculate score deterministically
        ratio = (passed_count / total_tc) if total_tc > 0 else 0.0
        score_awarded = round(ratio * max_marks, 2)

        # Map status
        if failure_type == "TIME_LIMIT_EXCEEDED":
            sub_status = SubmissionStatus.TIME_LIMIT_EXCEEDED
        elif failure_type == "MEMORY_LIMIT_EXCEEDED":
            sub_status = SubmissionStatus.MEMORY_LIMIT_EXCEEDED
        elif failure_type == "OUTPUT_LIMIT_EXCEEDED":
            sub_status = SubmissionStatus.OUTPUT_LIMIT_EXCEEDED
        elif failure_type == "SECURITY_VIOLATION":
            sub_status = SubmissionStatus.SECURITY_VIOLATION
        elif failure_type == "COMPILATION_ERROR":
            sub_status = SubmissionStatus.COMPILATION_ERROR
        elif passed_count == total_tc and total_tc > 0:
            sub_status = SubmissionStatus.COMPLETED
        elif failure_type == "RUNTIME_ERROR":
            sub_status = SubmissionStatus.RUNTIME_ERROR
        else:
            sub_status = SubmissionStatus.COMPLETED if passed_count > 0 else SubmissionStatus.FAILED

        # Build sanitized results (hidden test case inputs/outputs masked)
        raw_results = exec_res.get("results", [])
        sanitized_results = []
        total_exec_time = 0

        for r in raw_results:
            is_hid = r.get("is_hidden", False)
            total_exec_time += r.get("execution_time_ms", 0)
            sanitized_results.append({
                "test_case_index": r.get("test_case_index"),
                "passed": r.get("passed", False),
                "execution_time_ms": r.get("execution_time_ms", 0),
                "is_hidden": is_hid,
                "input": "[HIDDEN]" if is_hid else r.get("input"),
                "expected_output": "[HIDDEN]" if is_hid else r.get("expected_output"),
                "actual_output": ("[MATCH]" if r.get("passed") else "[MISMATCH]") if is_hid else r.get("actual_output"),
                "error": r.get("error")
            })

        submission.status = sub_status
        submission.passed_test_cases = passed_count
        submission.total_test_cases = total_tc
        submission.score_awarded = score_awarded
        submission.execution_time_ms = total_exec_time
        submission.results = sanitized_results
        submission.error_message = exec_res.get("error") or (
            f"Failed {total_tc - passed_count} of {total_tc} test cases ({sub_status.value})" if passed_count < total_tc else None
        )

        db.commit()
        db.refresh(submission)

        # 5. If linked to an active attempt, update AttemptAnswer record safely
        if attempt_id:
            ans = db.query(AttemptAnswer).filter(
                AttemptAnswer.attempt_id == attempt_id,
                AttemptAnswer.question_id == question_id
            ).first()
            if ans:
                ans.code_response = code
                ans.language = language
                ans.marks_awarded = score_awarded
                ans.is_correct = (passed_count == total_tc and total_tc > 0)
                ans.execution_result = {
                    "passed_test_cases": passed_count,
                    "total_test_cases": total_tc,
                    "all_passed": ans.is_correct,
                    "submission_id": submission.id,
                    "status": sub_status.value,
                    "results": sanitized_results
                }
                db.commit()

        return CodeSubmissionResponse(
            submission_id=submission.id,
            attempt_id=submission.attempt_id,
            question_id=submission.question_id,
            status=submission.status.value,
            total_test_cases=submission.total_test_cases,
            passed_test_cases=submission.passed_test_cases,
            score_awarded=submission.score_awarded,
            max_marks=submission.max_marks,
            execution_time_ms=submission.execution_time_ms,
            memory_used_kb=submission.memory_used_kb,
            results=[TestCaseResult(**item) for item in sanitized_results],
            error_message=submission.error_message,
            created_at=submission.created_at
        )

    @staticmethod
    def get_submission_status(db: Session, submission_id: str) -> CodeSubmissionResponse:
        sub = db.query(CodingSubmission).filter(CodingSubmission.id == submission_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Submission not found")

        return CodeSubmissionResponse(
            submission_id=sub.id,
            attempt_id=sub.attempt_id,
            question_id=sub.question_id,
            status=sub.status.value,
            total_test_cases=sub.total_test_cases,
            passed_test_cases=sub.passed_test_cases,
            score_awarded=sub.score_awarded,
            max_marks=sub.max_marks,
            execution_time_ms=sub.execution_time_ms,
            memory_used_kb=sub.memory_used_kb,
            results=[TestCaseResult(**item) for item in (sub.results or [])],
            error_message=sub.error_message,
            created_at=sub.created_at
        )

    @staticmethod
    def get_submission_history(
        db: Session,
        attempt_id: str,
        question_id: str
    ) -> List[CodeSubmissionResponse]:
        """
        Retrieves candidate submission history for a specific attempt question.
        """
        subs = db.query(CodingSubmission).filter(
            CodingSubmission.attempt_id == attempt_id,
            CodingSubmission.question_id == question_id
        ).order_by(CodingSubmission.created_at.desc()).all()

        return [
            CodeSubmissionResponse(
                submission_id=sub.id,
                attempt_id=sub.attempt_id,
                question_id=sub.question_id,
                status=sub.status.value,
                total_test_cases=sub.total_test_cases,
                passed_test_cases=sub.passed_test_cases,
                score_awarded=sub.score_awarded,
                max_marks=sub.max_marks,
                execution_time_ms=sub.execution_time_ms,
                memory_used_kb=sub.memory_used_kb,
                results=[TestCaseResult(**item) for item in (sub.results or [])],
                error_message=sub.error_message,
                created_at=sub.created_at
            )
            for sub in subs
        ]
