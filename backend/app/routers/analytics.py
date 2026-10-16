from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Role
from app.schemas.analytics import AssessmentAnalyticsResponse
from app.services.analytics_service import AnalyticsService
from app.dependencies import get_current_user, require_roles, verify_tenant_access

router = APIRouter(prefix="/analytics", tags=["Results, Rankings & Analytics"])


@router.get("/assessments/{assessment_id}", response_model=AssessmentAnalyticsResponse)
def get_assessment_analytics(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN, Role.PROCTOR))
):
    """
    Computes cohort rankings with tie-breakers, percentiles, and question-level metrics.
    """
    from app.models.assessment import Assessment
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    verify_tenant_access(assessment.org_id, current_user, db)
    return AnalyticsService.get_assessment_analytics(db, assessment_id)


@router.get("/recruiter/dashboard")
@router.get("/dashboard")
def get_recruiter_dashboard(
    org_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN))
):
    """
    Returns real-time aggregated metrics for the recruiter dashboard.
    """
    target_org = org_id or current_user.org_id
    if current_user.role != Role.PLATFORM_ADMIN and org_id and org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Cannot access dashboard metrics of another organization")
    return AnalyticsService.get_recruiter_dashboard_metrics(db, target_org)


@router.get("/assessments/{assessment_id}/export")
def export_assessment_report(
    assessment_id: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN, Role.PROCTOR))
):
    """
    Exports assessment candidate performance report in CSV or PDF format.
    Enforces strict role authorization and tenant isolation.
    """
    from app.services.evaluation_service import EvaluationService
    if format.lower() == "pdf":
        return EvaluationService.export_assessment_report_pdf(db, assessment_id, current_user)
    else:
        return EvaluationService.export_assessment_report_csv(db, assessment_id, current_user)

