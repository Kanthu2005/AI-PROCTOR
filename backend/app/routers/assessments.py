from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Role
from app.models.assessment import Assessment, AssessmentRule, AssessmentStatus
from app.schemas.assessment import (
    AssessmentCreate, AssessmentUpdate, AssessmentDetailResponse, AssessmentRuleSchema, AssessmentScheduleRequest
)
from app.services.assessment_service import AssessmentService
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/assessments", tags=["Assessment Authoring & Lifecycle"])

AUTHORIZED_ASSESSMENT_ROLES = [Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN]


def verify_assessment_access(assessment: Assessment, current_user: User):
    if current_user.role == Role.PLATFORM_ADMIN:
        return
    if current_user.org_id and assessment.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access assessments belonging to another organization"
        )


@router.post("", response_model=AssessmentDetailResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    assess_in: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    target_org = assess_in.org_id or current_user.org_id
    if current_user.role != Role.PLATFORM_ADMIN and target_org != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create assessment for another organization")
    assess_in.org_id = target_org
    assessment = AssessmentService.create_assessment(db, assess_in, user_id=current_user.id)
    return assessment


@router.get("", response_model=List[AssessmentDetailResponse])
def list_assessments(
    org_id: Optional[str] = None,
    status: Optional[AssessmentStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_org = org_id or current_user.org_id
    if current_user.role != Role.PLATFORM_ADMIN and org_id and org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot list assessments of another organization")
    query = db.query(Assessment).filter(Assessment.org_id == target_org)
    if status is not None:
        query = query.filter(Assessment.status == status)
    assessments = query.order_by(Assessment.created_at.desc()).all()
    return assessments


@router.get("/{assessment_id}", response_model=AssessmentDetailResponse)
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)
    return assessment


@router.get("/{assessment_id}/preview")
def preview_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES, Role.QUESTION_AUTHOR))
):
    """
    Candidate preview: sanitizes correct answers and explanations.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)
    return AssessmentService.get_candidate_assessment_view(db, assessment_id)


@router.put("/{assessment_id}", response_model=AssessmentDetailResponse)
def update_assessment(
    assessment_id: str,
    assess_update: AssessmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)

    if assessment.status in (AssessmentStatus.LIVE, AssessmentStatus.CLOSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit an assessment in {assessment.status.value} status to protect exam integrity."
        )

    if assess_update.title is not None:
        assessment.title = assess_update.title
    if assess_update.description is not None:
        assessment.description = assess_update.description
    if assess_update.instructions is not None:
        assessment.instructions = assess_update.instructions
    if assess_update.status is not None:
        assessment.status = assess_update.status
    if assess_update.total_duration_minutes is not None:
        assessment.total_duration_minutes = assess_update.total_duration_minutes
    if assess_update.total_marks is not None:
        assessment.total_marks = assess_update.total_marks
    if assess_update.passing_percentage is not None:
        assessment.passing_percentage = assess_update.passing_percentage
    if assess_update.start_time is not None:
        assessment.start_time = assess_update.start_time
    if assess_update.end_time is not None:
        assessment.end_time = assess_update.end_time
    if assess_update.max_attempts is not None:
        assessment.max_attempts = assess_update.max_attempts
    if assess_update.result_publication_policy is not None:
        assessment.result_publication_policy = assess_update.result_publication_policy
    if assess_update.is_active is not None:
        assessment.is_active = assess_update.is_active

    if assess_update.rules is not None and assessment.rules:
        r = assessment.rules
        u_r = assess_update.rules
        r.navigation_mode = u_r.navigation_mode
        r.section_wise_breaks = u_r.section_wise_breaks
        r.randomize_questions = u_r.randomize_questions
        r.randomize_options = u_r.randomize_options
        r.negative_marking_enabled = u_r.negative_marking_enabled
        r.negative_marking_formula = u_r.negative_marking_formula
        r.full_screen_enforced = u_r.full_screen_enforced
        r.max_tab_switches_allowed = u_r.max_tab_switches_allowed
        r.webcam_proctoring_enabled = u_r.webcam_proctoring_enabled
        r.devtools_block_enabled = u_r.devtools_block_enabled
        r.copy_paste_blocked = u_r.copy_paste_blocked

    db.commit()
    db.refresh(assessment)
    return assessment


@router.post("/{assessment_id}/publish", response_model=AssessmentDetailResponse)
def publish_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)
    return AssessmentService.publish_assessment(db, assessment_id)


@router.post("/{assessment_id}/schedule", response_model=AssessmentDetailResponse)
def schedule_assessment(
    assessment_id: str,
    sched_in: AssessmentScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)
    return AssessmentService.schedule_assessment(db, assessment_id, sched_in.start_time, sched_in.end_time)


@router.post("/{assessment_id}/live", response_model=AssessmentDetailResponse)
def go_live_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)
    return AssessmentService.go_live_assessment(db, assessment_id)


@router.post("/{assessment_id}/close", response_model=AssessmentDetailResponse)
def close_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)
    return AssessmentService.close_assessment(db, assessment_id)


@router.post("/{assessment_id}/duplicate", response_model=AssessmentDetailResponse, status_code=status.HTTP_201_CREATED)
def duplicate_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)
    return AssessmentService.duplicate_assessment(db, assessment_id, user_id=current_user.id)


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*AUTHORIZED_ASSESSMENT_ROLES))
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_assessment_access(assessment, current_user)

    if assessment.status in (AssessmentStatus.LIVE, AssessmentStatus.PUBLISHED) and len(assessment.attempts) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an assessment with active candidate attempts. Close it instead."
        )

    db.delete(assessment)
    db.commit()
    return None
