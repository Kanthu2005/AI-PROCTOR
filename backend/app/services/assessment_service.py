import random
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.assessment import Assessment, AssessmentRule, Section, SectionQuestion, NavigationMode, AssessmentStatus
from app.models.question import Question, QuestionVersion, QuestionType
from app.schemas.assessment import AssessmentCreate, AssessmentUpdate, AssessmentRuleSchema


class AssessmentService:
    @staticmethod
    def create_assessment(db: Session, assess_in: AssessmentCreate, user_id: Optional[str] = None) -> Assessment:
        assessment = Assessment(
            org_id=assess_in.org_id,
            title=assess_in.title,
            description=assess_in.description,
            instructions=assess_in.instructions,
            status=AssessmentStatus.DRAFT,
            version=1,
            total_duration_minutes=assess_in.total_duration_minutes,
            total_marks=assess_in.total_marks,
            passing_percentage=assess_in.passing_percentage,
            start_time=assess_in.start_time,
            end_time=assess_in.end_time,
            max_attempts=assess_in.max_attempts,
            result_publication_policy=assess_in.result_publication_policy,
            is_active=True,
            created_by_id=user_id
        )
        db.add(assessment)
        db.flush()

        # Rules
        rules_data = assess_in.rules or AssessmentRuleSchema()
        rule = AssessmentRule(
            assessment_id=assessment.id,
            navigation_mode=rules_data.navigation_mode,
            section_wise_breaks=rules_data.section_wise_breaks,
            randomize_questions=rules_data.randomize_questions,
            randomize_options=rules_data.randomize_options,
            negative_marking_enabled=rules_data.negative_marking_enabled,
            negative_marking_formula=rules_data.negative_marking_formula,
            full_screen_enforced=rules_data.full_screen_enforced,
            max_tab_switches_allowed=rules_data.max_tab_switches_allowed,
            webcam_proctoring_enabled=rules_data.webcam_proctoring_enabled,
            devtools_block_enabled=rules_data.devtools_block_enabled,
            copy_paste_blocked=rules_data.copy_paste_blocked,
            seb_required=rules_data.seb_required,
            seb_config_key=rules_data.seb_config_key,
            seb_browser_exam_keys=rules_data.seb_browser_exam_keys,
            seb_allow_quit=rules_data.seb_allow_quit,
            seb_quit_url=rules_data.seb_quit_url,
            seb_quit_password_hash=rules_data.seb_quit_password_hash
        )
        db.add(rule)

        # Sections and Section Questions
        for sec_in in assess_in.sections:
            section = Section(
                assessment_id=assessment.id,
                title=sec_in.title,
                duration_minutes=sec_in.duration_minutes,
                order_index=sec_in.order_index,
                cut_off_marks=sec_in.cut_off_marks
            )
            db.add(section)
            db.flush()

            for sq_in in sec_in.questions:
                # If question_version_id is not explicitly specified, lookup the question's current version
                q_version_id = sq_in.question_version_id
                if not q_version_id:
                    q = db.query(Question).filter(Question.id == sq_in.question_id).first()
                    if not q:
                        raise HTTPException(status_code=404, detail=f"Question {sq_in.question_id} not found")
                    current_v = db.query(QuestionVersion).filter(
                        QuestionVersion.question_id == q.id,
                        QuestionVersion.version_number == q.current_version_number
                    ).first()
                    if not current_v:
                        raise HTTPException(status_code=404, detail=f"No version found for question {q.id}")
                    q_version_id = current_v.id

                section_q = SectionQuestion(
                    section_id=section.id,
                    question_id=sq_in.question_id,
                    question_version_id=q_version_id,  # FROZEN version!
                    positive_marks=sq_in.positive_marks,
                    negative_marks=sq_in.negative_marks,
                    order_index=sq_in.order_index
                )
                db.add(section_q)

        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def publish_assessment(db: Session, assessment_id: str) -> Assessment:
        """
        Transitions an assessment to PUBLISHED state:
        - Validates legal transitions (only DRAFT or SCHEDULED can be published).
        - Validates that assessment has sections and at least one question.
        - Freezes the questions.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        if assessment.status not in (AssessmentStatus.DRAFT, AssessmentStatus.SCHEDULED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot publish assessment in {assessment.status.value} status. Only DRAFT or SCHEDULED can be published."
            )

        # Validation: must have at least one section and at least one question
        total_questions = sum(len(s.section_questions) for s in assessment.sections)
        if total_questions == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish an assessment with zero questions. Add questions before publishing."
            )

        assessment.status = AssessmentStatus.PUBLISHED
        assessment.is_active = True
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def schedule_assessment(db: Session, assessment_id: str, start_time: datetime, end_time: datetime) -> Assessment:
        """
        Schedules an assessment window.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        if assessment.status in (AssessmentStatus.CLOSED, AssessmentStatus.LIVE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot schedule assessment in {assessment.status.value} status."
            )

        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time must be strictly earlier than end_time."
            )

        total_questions = sum(len(s.section_questions) for s in assessment.sections)
        if total_questions == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule an assessment with zero questions. Add questions before scheduling."
            )

        assessment.start_time = start_time
        assessment.end_time = end_time
        assessment.status = AssessmentStatus.SCHEDULED
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def go_live_assessment(db: Session, assessment_id: str) -> Assessment:
        """
        Transitions an assessment to LIVE state:
        - Validates that assessment is PUBLISHED or SCHEDULED.
        - Validates that assessment has sections and at least one question.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        if assessment.status not in (AssessmentStatus.PUBLISHED, AssessmentStatus.SCHEDULED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition assessment in {assessment.status.value} status to LIVE. Must be PUBLISHED or SCHEDULED."
            )

        total_questions = sum(len(s.section_questions) for s in assessment.sections)
        if total_questions == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot launch a live assessment with zero questions. Add questions before going live."
            )

        assessment.status = AssessmentStatus.LIVE
        assessment.is_active = True
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def close_assessment(db: Session, assessment_id: str) -> Assessment:
        """
        Closes an assessment. No further attempts can be started.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        if assessment.status == AssessmentStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment is already CLOSED."
            )

        assessment.status = AssessmentStatus.CLOSED
        assessment.is_active = False
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def duplicate_assessment(db: Session, assessment_id: str, user_id: Optional[str] = None) -> Assessment:
        """
        Creates an independent duplicate copy of the assessment in DRAFT state.
        Clones sections, rules, and freezes the exact question version links.
        """
        source = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source assessment not found")

        new_assessment = Assessment(
            org_id=source.org_id,
            title=f"{source.title} (Copy)",
            description=source.description,
            instructions=source.instructions,
            status=AssessmentStatus.DRAFT,
            version=1,
            total_duration_minutes=source.total_duration_minutes,
            total_marks=source.total_marks,
            passing_percentage=source.passing_percentage,
            start_time=None,
            end_time=None,
            max_attempts=source.max_attempts,
            result_publication_policy=source.result_publication_policy,
            is_active=True,
            created_by_id=user_id
        )
        db.add(new_assessment)
        db.flush()

        # Duplicate Rules
        if source.rules:
            sr = source.rules
            new_rule = AssessmentRule(
                assessment_id=new_assessment.id,
                navigation_mode=sr.navigation_mode,
                section_wise_breaks=sr.section_wise_breaks,
                randomize_questions=sr.randomize_questions,
                randomize_options=sr.randomize_options,
                negative_marking_enabled=sr.negative_marking_enabled,
                negative_marking_formula=sr.negative_marking_formula,
                full_screen_enforced=sr.full_screen_enforced,
                max_tab_switches_allowed=sr.max_tab_switches_allowed,
                webcam_proctoring_enabled=sr.webcam_proctoring_enabled,
                devtools_block_enabled=sr.devtools_block_enabled,
                copy_paste_blocked=sr.copy_paste_blocked,
                seb_required=sr.seb_required,
                seb_config_key=sr.seb_config_key,
                seb_browser_exam_keys=sr.seb_browser_exam_keys,
                seb_allow_quit=sr.seb_allow_quit,
                seb_quit_url=sr.seb_quit_url,
                seb_quit_password_hash=sr.seb_quit_password_hash
            )
            db.add(new_rule)

        # Duplicate Sections & Section Questions
        for sec in source.sections:
            new_sec = Section(
                assessment_id=new_assessment.id,
                title=sec.title,
                duration_minutes=sec.duration_minutes,
                order_index=sec.order_index,
                cut_off_marks=sec.cut_off_marks
            )
            db.add(new_sec)
            db.flush()

            for sq in sec.section_questions:
                new_sq = SectionQuestion(
                    section_id=new_sec.id,
                    question_id=sq.question_id,
                    question_version_id=sq.question_version_id,
                    positive_marks=sq.positive_marks,
                    negative_marks=sq.negative_marks,
                    order_index=sq.order_index
                )
                db.add(new_sq)

        db.commit()
        db.refresh(new_assessment)
        return new_assessment

    @staticmethod
    def get_candidate_assessment_view(db: Session, assessment_id: str, candidate_seed: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves the assessment tailored for a candidate:
        - Applies randomization of questions/options if rules specify
        - Strips out `is_correct` answers and explanations to prevent cheating
        - Freezes navigation rules
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        rules = assessment.rules
        sections_data = []

        # Deterministic or random shuffle based on candidate attempt
        rng = random.Random(candidate_seed) if candidate_seed else random.Random()

        for sec in assessment.sections:
            sq_list = list(sec.section_questions)
            if rules and rules.randomize_questions:
                rng.shuffle(sq_list)

            questions_payload = []
            for sq in sq_list:
                qv = sq.question_version
                # Prepare sanitized options without answer leaks
                sanitized_options = []
                if qv.options:
                    raw_opts = list(qv.options)
                    if rules and rules.randomize_options:
                        rng.shuffle(raw_opts)
                    for opt in raw_opts:
                        sanitized_options.append({
                            "id": opt.get("id"),
                            "text": opt.get("text")
                        })

                # Sanitize coding details (strip hidden test cases from candidate payload)
                sanitized_coding = {}
                if qv.coding_details:
                    sanitized_coding = {
                        "starter_code": qv.coding_details.get("starter_code", ""),
                        "language": qv.coding_details.get("language", "python"),
                        "public_test_cases": [
                            tc for tc in qv.coding_details.get("test_cases", [])
                            if not tc.get("is_hidden", False)
                        ]
                    }

                # Sanitize SQL details (strictly exclude solution_sql to prevent cheating)
                sanitized_sql = {}
                if qv.sql_details:
                    sanitized_sql = {
                        "schema_sql": qv.sql_details.get("schema_sql", ""),
                        "test_queries": qv.sql_details.get("test_queries", [])
                    }

                questions_payload.append({
                    "section_question_id": sq.id,
                    "question_id": sq.question_id,
                    "question_version_id": sq.question_version_id,
                    "title": qv.title,
                    "description": qv.description,
                    "question_type": qv.question_type.value,
                    "positive_marks": sq.positive_marks,
                    "negative_marks": sq.negative_marks,
                    "options": sanitized_options,
                    "coding_details": sanitized_coding,
                    "sql_details": sanitized_sql,
                    "order_index": sq.order_index
                })

            sections_data.append({
                "id": sec.id,
                "title": sec.title,
                "duration_minutes": sec.duration_minutes,
                "order_index": sec.order_index,
                "cut_off_marks": sec.cut_off_marks,
                "questions": questions_payload
            })

        return {
            "id": assessment.id,
            "title": assessment.title,
            "description": assessment.description,
            "instructions": assessment.instructions,
            "total_duration_minutes": assessment.total_duration_minutes,
            "rules": {
                "navigation_mode": rules.navigation_mode.value if rules else "FREE",
                "section_wise_breaks": rules.section_wise_breaks if rules else False,
                "negative_marking_enabled": rules.negative_marking_enabled if rules else True,
                "full_screen_enforced": rules.full_screen_enforced if rules else True,
                "max_tab_switches_allowed": rules.max_tab_switches_allowed if rules else 3,
                "webcam_proctoring_enabled": rules.webcam_proctoring_enabled if rules else True,
                "devtools_block_enabled": rules.devtools_block_enabled if rules else True,
                "copy_paste_blocked": rules.copy_paste_blocked if rules else True,
                "seb_required": rules.seb_required if rules else False,
                "seb_allow_quit": rules.seb_allow_quit if rules else True
            },
            "sections": sections_data
        }

    @staticmethod
    def calculate_mcq_score(
        selected_option_ids: List[str],
        correct_option_ids: List[str],
        positive_marks: float,
        negative_marks: float,
        negative_marking_enabled: bool = True
    ) -> Tuple[bool, float]:
        """
        Evaluates MCQ score:
        - If candidate selected nothing: 0 marks (not penalized)
        - If exact match: correct=1, wrong=0 -> positive_marks
        - If incorrect: correct=0, wrong=1 -> -1 * negative_marks (if negative marking enabled)
        """
        if not selected_option_ids:
            return False, 0.0

        is_correct = set(selected_option_ids) == set(correct_option_ids)
        if is_correct:
            return True, float(positive_marks)
        else:
            deduction = float(negative_marks) if negative_marking_enabled else 0.0
            return False, -deduction
