import re
import difflib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus
from app.models.assessment import Assessment
from app.models.question import Question, QuestionType


class CodeSimilarityService:
    """
    Submissions Code Similarity Analyzer for Recruiters.
    Calculates pairwise tokenized/structural similarity between candidate submissions
    for coding questions within an assessment.
    
    CRITICAL POLICY:
    Similarity is strictly an advisory review signal, never automated proof of misconduct.
    """

    @staticmethod
    def normalize_code(code: str) -> str:
        """
        Normalizes source code by removing comments, docstrings, and collapsing whitespace.
        """
        if not code:
            return ""
        # Remove single-line comments (# ... or // ...)
        code = re.sub(r'(#|//).*', '', code)
        # Remove multi-line comments (/* ... */ or '''...''' or \"\"\"...\"\"\")
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'(\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?""")', '', code)
        # Collapse multiple whitespaces and newlines
        code = re.sub(r'\s+', ' ', code)
        return code.strip()

    @classmethod
    def calculate_similarity(cls, code1: str, code2: str) -> float:
        """
        Calculates similarity ratio between 0.0 and 1.0 using normalized token sequence matching.
        """
        norm1 = cls.normalize_code(code1)
        norm2 = cls.normalize_code(code2)

        if not norm1 or not norm2:
            return 0.0
        if norm1 == norm2:
            return 1.0

        matcher = difflib.SequenceMatcher(None, norm1, norm2)
        return round(matcher.ratio(), 3)

    @classmethod
    def analyze_assessment_code_similarity(
        cls,
        db: Session,
        assessment_id: str,
        question_id: Optional[str] = None,
        threshold: float = 0.70
    ) -> Dict[str, Any]:
        """
        Performs cohort-wide code similarity comparison across all submitted candidate attempts.
        Returns pairwise similarity rankings, cluster matches, and reviewer advisory notices.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            return {"error": "Assessment not found", "pairs": []}

        # Query all submitted attempts for this assessment
        query = db.query(AttemptAnswer, Attempt).join(
            Attempt, AttemptAnswer.attempt_id == Attempt.id
        ).filter(
            Attempt.assessment_id == assessment_id,
            Attempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED])
        )

        if question_id:
            query = query.filter(AttemptAnswer.question_id == question_id)

        answers = query.all()

        # Group answers by question_id
        grouped_by_q: Dict[str, List[Dict[str, Any]]] = {}
        for ans, att in answers:
            code = (ans.code_response or "").strip()
            if not code or len(code) < 15:
                continue
            qid = ans.question_id
            if qid not in grouped_by_q:
                grouped_by_q[qid] = []
            grouped_by_q[qid].append({
                "attempt_id": att.id,
                "candidate_name": att.candidate_name,
                "candidate_email": att.candidate_email,
                "submitted_at": att.submitted_at.isoformat() if att.submitted_at else None,
                "code": code
            })

        flagged_pairs = []
        total_comparisons = 0

        for qid, submissions in grouped_by_q.items():
            n = len(submissions)
            for i in range(n):
                for j in range(i + 1, n):
                    total_comparisons += 1
                    sub_a = submissions[i]
                    sub_b = submissions[j]
                    sim = cls.calculate_similarity(sub_a["code"], sub_b["code"])

                    if sim >= threshold:
                        tier = "SUSPICIOUS_MATCH" if sim >= 0.85 else "MODERATE_SIMILARITY"
                        flagged_pairs.append({
                            "question_id": qid,
                            "candidate_a": {
                                "attempt_id": sub_a["attempt_id"],
                                "name": sub_a["candidate_name"],
                                "email": sub_a["candidate_email"],
                                "submitted_at": sub_a["submitted_at"]
                            },
                            "candidate_b": {
                                "attempt_id": sub_b["attempt_id"],
                                "name": sub_b["candidate_name"],
                                "email": sub_b["candidate_email"],
                                "submitted_at": sub_b["submitted_at"]
                            },
                            "similarity_score": sim,
                            "similarity_percentage": f"{round(sim * 100, 1)}%",
                            "review_tier": tier,
                            "investigation_recommended": sim >= 0.85
                        })

        # Sort pairs highest similarity first
        flagged_pairs.sort(key=lambda x: x["similarity_score"], reverse=True)

        return {
            "assessment_id": assessment_id,
            "total_submissions_analyzed": sum(len(subs) for subs in grouped_by_q.values()),
            "total_pairwise_comparisons": total_comparisons,
            "threshold_applied": threshold,
            "flagged_pairs_count": len(flagged_pairs),
            "flagged_pairs": flagged_pairs,
            "review_signal_only": True,
            "disclaimer": (
                "Code similarity is an investigative advisory signal for recruiter review, "
                "not definitive proof of misconduct or plagiarism. Shared standard libraries, "
                "boilerplate templates, and canonical algorithms naturally produce moderate similarity."
            )
        }
