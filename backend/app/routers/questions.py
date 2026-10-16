import math
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Role
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel, ReviewStatus
from app.schemas.question import (
    QuestionCreate, QuestionUpdate, QuestionResponse, QuestionVersionResponse, QuestionReviewRequest, PaginatedQuestionResponse
)
from app.services.question_service import QuestionService
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/questions", tags=["Question Bank & Versioning"])

AUTHORIZED_QUESTION_ROLES = [Role.QUESTION_AUTHOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN]


def verify_question_access(question: Question, current_user: User):
    if current_user.role == Role.PLATFORM_ADMIN:
        return
    if current_user.org_id and question.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access questions belonging to another organization"
        )


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    q_in: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_QUESTION_ROLES))
):
    target_org = q_in.org_id or current_user.org_id
    if current_user.role != Role.PLATFORM_ADMIN and target_org != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create question for another organization")
    q_in.org_id = target_org
    question = QuestionService.create_question(db, q_in, user_id=current_user.id)
    # Load current version
    current_v = db.query(QuestionVersion).filter(
        QuestionVersion.question_id == question.id,
        QuestionVersion.version_number == question.current_version_number
    ).first()
    
    return QuestionResponse(
        id=question.id,
        org_id=question.org_id,
        question_type=question.question_type,
        current_version_number=question.current_version_number,
        is_active=question.is_active,
        created_at=question.created_at,
        current_version=QuestionVersionResponse.model_validate(current_v) if current_v else None
    )


@router.put("/{question_id}", response_model=QuestionVersionResponse)
def update_question(
    question_id: str,
    q_update: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_QUESTION_ROLES))
):
    """
    Editing a question generates a NEW QuestionVersion (incrementing version number).
    Existing assessments referencing previous versions remain immutable.
    """
    question = QuestionService.get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    verify_question_access(question, current_user)

    new_version = QuestionService.update_question(db, question_id, q_update, user_id=current_user.id)
    return new_version


@router.post("/{question_id}/review", response_model=QuestionVersionResponse)
def review_question(
    question_id: str,
    review_in: QuestionReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Question review gate: Recruiter / Org Admin approves or publishes author submissions.
    """
    question = QuestionService.get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    verify_question_access(question, current_user)

    v = QuestionService.review_question(db, question_id, review_in.review_status, user_id=current_user.id)
    return v


@router.post("/{question_id}/duplicate", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def duplicate_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_QUESTION_ROLES))
):
    question = QuestionService.get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    verify_question_access(question, current_user)

    new_q = QuestionService.duplicate_question(db, question_id, user_id=current_user.id)
    current_v = db.query(QuestionVersion).filter(
        QuestionVersion.question_id == new_q.id,
        QuestionVersion.version_number == new_q.current_version_number
    ).first()

    return QuestionResponse(
        id=new_q.id,
        org_id=new_q.org_id,
        question_type=new_q.question_type,
        current_version_number=new_q.current_version_number,
        is_active=new_q.is_active,
        created_at=new_q.created_at,
        current_version=QuestionVersionResponse.model_validate(current_v) if current_v else None
    )


@router.get("", response_model=Union[PaginatedQuestionResponse, List[QuestionResponse]])
def list_questions(
    response: Response,
    org_id: Optional[str] = Query(None),
    question_type: Optional[QuestionType] = Query(None),
    difficulty: Optional[DifficultyLevel] = Query(None),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    review_status: Optional[ReviewStatus] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    paginated: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_org = org_id or current_user.org_id
    if current_user.role != Role.PLATFORM_ADMIN and org_id and org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view questions from another organization")

    questions, total_count = QuestionService.list_questions(
        db, target_org,
        question_type=question_type,
        difficulty=difficulty,
        search=search,
        tag=tag,
        topic=topic,
        review_status=review_status,
        page=page,
        page_size=page_size
    )

    items = []
    for q in questions:
        current_v = db.query(QuestionVersion).filter(
            QuestionVersion.question_id == q.id,
            QuestionVersion.version_number == q.current_version_number
        ).first()
        items.append(QuestionResponse(
            id=q.id,
            org_id=q.org_id,
            question_type=q.question_type,
            current_version_number=q.current_version_number,
            is_active=q.is_active,
            created_at=q.created_at,
            current_version=QuestionVersionResponse.model_validate(current_v) if current_v else None
        ))

    effective_page = page or 1
    effective_page_size = page_size or (total_count if total_count > 0 else 10)
    total_pages = max(1, math.ceil(total_count / effective_page_size)) if total_count > 0 else 1

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Page"] = str(effective_page)
    response.headers["X-Page-Size"] = str(effective_page_size)
    response.headers["X-Total-Pages"] = str(total_pages)

    if paginated is True or page is not None:
        return PaginatedQuestionResponse(
            items=items,
            total=total_count,
            page=effective_page,
            page_size=effective_page_size,
            total_pages=total_pages
        )

    return items


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = QuestionService.get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    verify_question_access(question, current_user)

    current_v = db.query(QuestionVersion).filter(
        QuestionVersion.question_id == question.id,
        QuestionVersion.version_number == question.current_version_number
    ).first()

    all_v = db.query(QuestionVersion).filter(
        QuestionVersion.question_id == question.id
    ).order_by(QuestionVersion.version_number.desc()).all()

    return QuestionResponse(
        id=question.id,
        org_id=question.org_id,
        question_type=question.question_type,
        current_version_number=question.current_version_number,
        is_active=question.is_active,
        created_at=question.created_at,
        current_version=QuestionVersionResponse.model_validate(current_v) if current_v else None,
        all_versions=[QuestionVersionResponse.model_validate(v) for v in all_v]
    )


@router.get("/{question_id}/versions/{version_id}", response_model=QuestionVersionResponse)
def get_question_version(
    question_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = QuestionService.get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    verify_question_access(question, current_user)

    v = QuestionService.get_question_version(db, version_id)
    if not v or v.question_id != question_id:
        raise HTTPException(status_code=404, detail="Question version not found")
    return v


@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_QUESTION_ROLES))
):
    question = QuestionService.get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    verify_question_access(question, current_user)

    question.is_active = False
    db.commit()
    return {"message": "Question successfully deleted"}


