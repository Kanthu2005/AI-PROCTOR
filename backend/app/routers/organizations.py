from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import Organization, User, Role
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from app.dependencies import get_current_user, require_roles, verify_tenant_access

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PLATFORM_ADMIN, Role.ORG_ADMIN))
):
    existing = db.query(Organization).filter(Organization.slug == org_in.slug.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization with this slug already exists")

    org = Organization(
        name=org_in.name,
        slug=org_in.slug.lower(),
        domain=org_in.domain,
        is_active=True
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("", response_model=List[OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PLATFORM_ADMIN))
):
    return db.query(Organization).all()


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    verify_tenant_access(org_id, current_user, db)
    return org

