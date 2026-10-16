from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, Role, SecurityAuditEvent
from app.schemas.auth import (
    UserCreate, UserResponse, LoginRequest, Token, RefreshTokenRequest,
    PasswordResetRequest, PasswordResetConfirm, SecurityAuditResponse
)
from app.services.auth_service import AuthService
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    """Sets secure HttpOnly cookies for access and refresh tokens along with CSRF token."""
    cookie_kwargs = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    # Short-lived access token cookie
    response.set_cookie(
        key=settings.COOKIE_ACCESS_TOKEN_KEY,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs
    )
    # Refresh token cookie
    response.set_cookie(
        key=settings.COOKIE_REFRESH_TOKEN_KEY,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **cookie_kwargs
    )
    # CSRF cookie (readable by JS to include in X-CSRF-Token header)
    response.set_cookie(
        key=settings.COOKIE_CSRF_TOKEN_KEY,
        value=csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clears all session authentication and CSRF cookies."""
    response.delete_cookie(key=settings.COOKIE_ACCESS_TOKEN_KEY, httponly=True, samesite=settings.COOKIE_SAMESITE)
    response.delete_cookie(key=settings.COOKIE_REFRESH_TOKEN_KEY, httponly=True, samesite=settings.COOKIE_SAMESITE)
    response.delete_cookie(key=settings.COOKIE_CSRF_TOKEN_KEY, httponly=False, samesite=settings.COOKIE_SAMESITE)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Registers a new user account with Argon2id password hashing."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AuthService.register_user(db, user_in, ip_address=client_ip, user_agent=user_agent)


@router.post("/login", response_model=Token)
def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticates user, issues short-lived access token, refresh token,
    and sets secure HttpOnly cookies with CSRF token.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    token_obj, refresh_str, csrf_str = AuthService.authenticate_user(
        db, login_data, ip_address=client_ip, user_agent=user_agent
    )
    _set_auth_cookies(response, token_obj.access_token, refresh_str, csrf_str)
    return token_obj


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    response: Response,
    refresh_in: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Rotates refresh token and issues a fresh short-lived access token.
    Accepts token from JSON payload or 'proctorai_refresh_token' HttpOnly cookie.
    """
    token_str = None
    if refresh_in and refresh_in.refresh_token:
        token_str = refresh_in.refresh_token
    elif "proctorai_refresh_token" in request.cookies:
        token_str = request.cookies.get("proctorai_refresh_token")

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required"
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    token_obj, new_refresh_str, new_csrf_str = AuthService.refresh_access_token(
        db, token_str, ip_address=client_ip, user_agent=user_agent
    )
    _set_auth_cookies(response, token_obj.access_token, new_refresh_str, new_csrf_str)
    return token_obj


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logs out the authenticated user, revokes active refresh tokens,
    and clears HttpOnly authentication cookies.
    """
    token_str = request.cookies.get("proctorai_refresh_token")
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    AuthService.logout_user(
        db, user_id=current_user.id, refresh_token_str=token_str,
        ip_address=client_ip, user_agent=user_agent
    )
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile and organization membership."""
    return current_user


@router.post("/password-reset/request")
def request_password_reset(
    reset_req: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Dispatches a single-use password reset token with short expiration.
    Returns safe generic message preventing email enumeration.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AuthService.request_password_reset(
        db, email=reset_req.email, ip_address=client_ip, user_agent=user_agent
    )


@router.post("/password-reset/confirm")
def confirm_password_reset(
    reset_in: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Confirms password reset using a valid single-use token,
    updates user password with Argon2id, and invalidates all existing sessions.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AuthService.confirm_password_reset(
        db, reset_in, ip_address=client_ip, user_agent=user_agent
    )


@router.get("/audit-logs", response_model=List[SecurityAuditResponse])
def get_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.PLATFORM_ADMIN, Role.ORG_ADMIN))
):
    """
    Retrieves security audit event logs.
    Platform Admin has universal access; Org Admin is scoped to their organization.
    """
    query = db.query(SecurityAuditEvent)
    if current_user.role != Role.PLATFORM_ADMIN:
        query = query.filter(SecurityAuditEvent.org_id == current_user.org_id)
    return query.order_by(SecurityAuditEvent.created_at.desc()).limit(limit).all()
