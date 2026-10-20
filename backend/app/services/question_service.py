from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel, ReviewStatus
from app.schemas.question import QuestionCreate, QuestionUpdate


class QuestionService:
    @staticmethod
    def create_question(db: Session, q_in: QuestionCreate, user_id: Optional[str] = None) -> Question:
        """
        Creates a parent Question entry and its initial immutable Version 1.
        """
        question = Question(
            org_id=q_in.org_id,
            question_type=q_in.question_type,
            current_version_number=1,
            is_active=True
        )
        db.add(question)
        db.flush()

        initial_version = QuestionVersion(
            question_id=question.id,
            version_number=1,
            title=q_in.title,
            description=q_in.description,
            question_type=q_in.question_type,
            difficulty=q_in.difficulty,
            default_positive_marks=q_in.default_positive_marks,
            default_negative_marks=q_in.default_negative_marks,
            tags=q_in.tags,
            topic=q_in.topic or "General",
            explanation=q_in.explanation,
            options=[opt.model_dump() for opt in q_in.options] if q_in.options else [],
            coding_details=q_in.coding_details.model_dump() if q_in.coding_details else {},
            sql_details=q_in.sql_details.model_dump() if q_in.sql_details else {},
            descriptive_details=q_in.descriptive_details.model_dump() if q_in.descriptive_details else {},
            review_status=q_in.review_status,
            is_published=q_in.is_published,
            created_by_id=user_id
        )
        db.add(initial_version)
        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def update_question(db: Session, question_id: str, q_update: QuestionUpdate, user_id: Optional[str] = None) -> QuestionVersion:
        """
        Modifies a question by spawning a NEW QuestionVersion with an incremented version_number.
        Historical assessments linked to previous version IDs remain completely unchanged and preserved.
        """
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )

        # Get latest current version
        latest_version = db.query(QuestionVersion).filter(
            QuestionVersion.question_id == question_id,
            QuestionVersion.version_number == question.current_version_number
        ).first()

        new_version_num = question.current_version_number + 1

        # Validate options if updated
        target_type = latest_version.question_type
        if q_update.options is not None:
            if target_type == QuestionType.MCQ_SINGLE:
                if len(q_update.options) < 2:
                    raise HTTPException(status_code=400, detail="MCQ_SINGLE requires at least 2 options")
                correct = sum(1 for o in q_update.options if o.is_correct)
                if correct != 1:
                    raise HTTPException(status_code=400, detail=f"MCQ_SINGLE must have exactly 1 correct option, found {correct}")
            elif target_type == QuestionType.MCQ_MULTIPLE:
                if len(q_update.options) < 2:
                    raise HTTPException(status_code=400, detail="MCQ_MULTIPLE requires at least 2 options")
                correct = sum(1 for o in q_update.options if o.is_correct)
                if correct < 1:
                    raise HTTPException(status_code=400, detail="MCQ_MULTIPLE must have at least 1 correct option")
            elif target_type == QuestionType.TRUE_FALSE:
                if len(q_update.options) != 2:
                    raise HTTPException(status_code=400, detail="TRUE_FALSE question must have exactly 2 options")
                correct = sum(1 for o in q_update.options if o.is_correct)
                if correct != 1:
                    raise HTTPException(status_code=400, detail="TRUE_FALSE question must have exactly 1 correct option")

        if q_update.coding_details is not None and target_type == QuestionType.CODING:
            if not q_update.coding_details.test_cases:
                raise HTTPException(status_code=400, detail="Python CODING questions must have at least 1 test case")
            for idx, tc in enumerate(q_update.coding_details.test_cases):
                if tc.expected_output is None or str(tc.expected_output).strip() == "":
                    raise HTTPException(status_code=400, detail=f"Test case #{idx + 1} must have a non-empty expected_output")

        # Use new fields if provided, else copy from latest version
        new_version = QuestionVersion(
            question_id=question.id,
            version_number=new_version_num,
            title=q_update.title if q_update.title is not None else latest_version.title,
            description=q_update.description if q_update.description is not None else latest_version.description,
            question_type=latest_version.question_type,
            difficulty=q_update.difficulty if q_update.difficulty is not None else latest_version.difficulty,
            default_positive_marks=q_update.default_positive_marks if q_update.default_positive_marks is not None else latest_version.default_positive_marks,
            default_negative_marks=q_update.default_negative_marks if q_update.default_negative_marks is not None else latest_version.default_negative_marks,
            tags=q_update.tags if q_update.tags is not None else latest_version.tags,
            topic=q_update.topic if q_update.topic is not None else getattr(latest_version, "topic", "General"),
            explanation=q_update.explanation if q_update.explanation is not None else latest_version.explanation,
            options=[opt.model_dump() for opt in q_update.options] if q_update.options is not None else latest_version.options,
            coding_details=q_update.coding_details.model_dump() if q_update.coding_details is not None else latest_version.coding_details,
            sql_details=q_update.sql_details.model_dump() if q_update.sql_details is not None else latest_version.sql_details,
            descriptive_details=q_update.descriptive_details.model_dump() if q_update.descriptive_details is not None else getattr(latest_version, "descriptive_details", {}),
            review_status=q_update.review_status if q_update.review_status is not None else latest_version.review_status,
            is_published=q_update.is_published if q_update.is_published is not None else latest_version.is_published,
            created_by_id=user_id
        )

        db.add(new_version)
        question.current_version_number = new_version_num
        db.commit()
        db.refresh(new_version)
        return new_version

    @staticmethod
    def review_question(db: Session, question_id: str, review_status: ReviewStatus, user_id: Optional[str] = None) -> QuestionVersion:
        """
        Updates review status of the question's latest active version.
        """
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        current_v = db.query(QuestionVersion).filter(
            QuestionVersion.question_id == question.id,
            QuestionVersion.version_number == question.current_version_number
        ).first()

        if not current_v:
            raise HTTPException(status_code=404, detail="Question version not found")

        current_v.review_status = review_status
        db.commit()
        db.refresh(current_v)
        return current_v

    @staticmethod
    def duplicate_question(db: Session, question_id: str, user_id: Optional[str] = None) -> Question:
        """
        Clones an existing question and its latest version to allow easy authoring of variations.
        """
        source_q = db.query(Question).filter(Question.id == question_id).first()
        if not source_q:
            raise HTTPException(status_code=404, detail="Question to duplicate not found")

        source_v = db.query(QuestionVersion).filter(
            QuestionVersion.question_id == source_q.id,
            QuestionVersion.version_number == source_q.current_version_number
        ).first()

        new_q = Question(
            org_id=source_q.org_id,
            question_type=source_q.question_type,
            current_version_number=1,
            is_active=True
        )
        db.add(new_q)
        db.flush()

        new_v = QuestionVersion(
            question_id=new_q.id,
            version_number=1,
            title=f"{source_v.title} (Copy)",
            description=source_v.description,
            question_type=source_v.question_type,
            difficulty=source_v.difficulty,
            default_positive_marks=source_v.default_positive_marks,
            default_negative_marks=source_v.default_negative_marks,
            tags=list(source_v.tags) if source_v.tags else [],
            topic=getattr(source_v, "topic", "General"),
            explanation=source_v.explanation,
            options=list(source_v.options) if source_v.options else [],
            coding_details=dict(source_v.coding_details) if source_v.coding_details else {},
            sql_details=dict(source_v.sql_details) if source_v.sql_details else {},
            review_status=ReviewStatus.DRAFT,
            is_published=False,
            created_by_id=user_id
        )
        db.add(new_v)
        db.commit()
        db.refresh(new_q)
        return new_q

    @staticmethod
    def get_question(db: Session, question_id: str) -> Optional[Question]:
        return db.query(Question).filter(Question.id == question_id).first()

    @staticmethod
    def get_question_version(db: Session, version_id: str) -> Optional[QuestionVersion]:
        return db.query(QuestionVersion).filter(QuestionVersion.id == version_id).first()

    @staticmethod
    def list_questions(
        db: Session,
        org_id: str,
        question_type: Optional[QuestionType] = None,
        difficulty: Optional[DifficultyLevel] = None,
        search: Optional[str] = None,
        tag: Optional[str] = None,
        topic: Optional[str] = None,
        review_status: Optional[ReviewStatus] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
    ) -> tuple[List[Question], int]:
        query = db.query(Question).filter(Question.org_id == org_id, Question.is_active == True)
        if question_type:
            query = query.filter(Question.question_type == question_type)

        questions = query.all()
        # Further filter by latest version attributes if needed
        filtered = []
        for q in questions:
            v = db.query(QuestionVersion).filter(
                QuestionVersion.question_id == q.id,
                QuestionVersion.version_number == q.current_version_number
            ).first()
            if not v:
                continue
            if difficulty and v.difficulty != difficulty:
                continue
            if review_status and v.review_status != review_status:
                continue
            if tag and (not v.tags or tag.lower() not in [t.lower() for t in v.tags]):
                continue
            if topic:
                v_topic = getattr(v, "topic", "") or ""
                if topic.lower() not in v_topic.lower():
                    continue
            if search:
                s_lower = search.lower()
                title_match = s_lower in v.title.lower()
                desc_match = s_lower in (v.description or "").lower()
                topic_match = s_lower in (getattr(v, "topic", "") or "").lower()
                tags_match = any(s_lower in t.lower() for t in (v.tags or []))
                if not (title_match or desc_match or topic_match or tags_match):
                    continue
            filtered.append(q)

        total_count = len(filtered)
        if page is not None and page_size is not None and page_size > 0:
            start = (page - 1) * page_size
            end = start + page_size
            return filtered[start:end], total_count

        return filtered, total_count
