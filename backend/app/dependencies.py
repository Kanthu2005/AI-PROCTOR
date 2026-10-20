from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, Role
from app.utils.security import decode_access_token
from app.services.audit_service import AuditService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Extracts and validates authenticated user from either:
    1. HTTP Authorization Header ('Bearer <token>')
    2. Secure HttpOnly Cookie ('proctorai_access_token') with CSRF verification
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    resolved_token = token
    from_cookie = False

    # Check HttpOnly cookie if header is absent
    if not resolved_token and request:
        resolved_token = request.cookies.get(settings.COOKIE_ACCESS_TOKEN_KEY)
        if resolved_token:
            from_cookie = True

    if not resolved_token:
        raise credentials_exception

    # If authenticated via cookie for state-modifying requests, verify CSRF token
    if from_cookie and settings.CSRF_PROTECTION_ENABLED and request:
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            csrf_cookie = request.cookies.get(settings.COOKIE_CSRF_TOKEN_KEY)
            csrf_header = request.headers.get("x-csrf-token") or request.headers.get("X-CSRF-Token")
            if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF validation failed for cookie-authenticated session"
                )

    payload = decode_access_token(resolved_token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*allowed_roles: Role):
    """
    Role-Based Access Control dependency factory.
    Platform Admin has universal access.
    Supports consolidated ADMIN_RECRUITER role and legacy mapped roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == Role.PLATFORM_ADMIN:
            return current_user
        
        effective_user_role = Role.normalize(current_user.role)
        normalized_allowed = {Role.normalize(r) for r in allowed_roles}

        if current_user.role not in allowed_roles and effective_user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


def verify_tenant_access(
    target_org_id: Optional[str],
    current_user: User,
    db: Session,
    request: Optional[Request] = None
) -> None:
    """
    Enforces multi-tenant data isolation and prevents IDOR vulnerabilities.
    Raises HTTP 403 Forbidden if user attempts cross-organization access.
    """
    if current_user.role == Role.PLATFORM_ADMIN:
        return

    if target_org_id and current_user.org_id != target_org_id:
        client_ip = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        AuditService.log_event(
            db=db,
            event_type="CROSS_TENANT_ACCESS_BLOCKED",
            user_id=current_user.id,
            email=current_user.email,
            org_id=current_user.org_id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"attempted_org_id": target_org_id}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot access resources belonging to another organization"
        )
