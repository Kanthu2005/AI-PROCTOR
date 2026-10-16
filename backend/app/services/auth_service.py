import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User, Organization, Role, RefreshToken, PasswordResetToken
from app.schemas.auth import (
    UserCreate, LoginRequest, Token, PasswordResetConfirm
)
from app.utils.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, generate_reset_token, generate_csrf_token
)
from app.services.audit_service import AuditService


class AuthRateLimiter:
    """
    In-memory sliding-window rate limiter for sensitive authentication operations
    (login attempts, password reset requests).
    Protects against brute-force password guessing and credential stuffing attacks.
    """
    _attempts: Dict[str, List[float]] = {}

    @classmethod
    def check_rate_limit(cls, identifier: str, limit_per_minute: Optional[int] = None) -> Tuple[bool, int]:
        max_limit = limit_per_minute or settings.AUTH_RATE_LIMIT_PER_MINUTE
        now = time.time()
        window_start = now - 60.0

        if identifier not in cls._attempts:
            cls._attempts[identifier] = []

        valid_timestamps = [t for t in cls._attempts[identifier] if t > window_start]
        cls._attempts[identifier] = valid_timestamps

        if len(valid_timestamps) >= max_limit:
            retry_after = max(1, int(60.0 - (now - valid_timestamps[0])))
            return False, retry_after

        cls._attempts[identifier].append(now)
        return True, 0

    @classmethod
    def reset(cls):
        cls._attempts.clear()


class AuthService:
    @staticmethod
    def register_user(
        db: Session,
        user_in: UserCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> User:
        existing = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        # If org_id is provided, verify it exists; otherwise assign to default workspace
        assigned_org_id = user_in.org_id
        if assigned_org_id:
            org = db.query(Organization).filter(Organization.id == assigned_org_id).first()
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )
        elif user_in.role != Role.PLATFORM_ADMIN:
            default_org = db.query(Organization).first()
            if not default_org:
                default_org = Organization(
                    name="Default Workspace",
                    slug="default-workspace",
                    domain="workspace.local",
                    is_active=True
                )
                db.add(default_org)
                db.flush()
            assigned_org_id = default_org.id

        new_user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name,
            role=user_in.role,
            org_id=assigned_org_id,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        AuditService.log_event(
            db=db,
            event_type="USER_REGISTERED",
            user_id=new_user.id,
            email=new_user.email,
            org_id=new_user.org_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"role": new_user.role.value}
        )

        return new_user

    @staticmethod
    def authenticate_user(
        db: Session,
        login_data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Token, str, str]:
        email = login_data.email.lower().strip()

        # Brute-force rate limiting protection
        rate_key = f"auth:{ip_address or 'unknown'}:{email}"
        allowed, retry_after = AuthRateLimiter.check_rate_limit(rate_key)
        if not allowed:
            AuditService.log_event(
                db=db,
                event_type="LOGIN_RATE_LIMITED",
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"retry_after": retry_after}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Please retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

        user = db.query(User).filter(User.email == email).first()

        if not user or not verify_password(login_data.password, user.hashed_password):
            AuditService.log_event(
                db=db,
                event_type="LOGIN_FAILED",
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                details="Invalid email or password"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user.is_active:
            AuditService.log_event(
                db=db,
                event_type="LOGIN_FAILED_INACTIVE",
                user_id=user.id,
                email=user.email,
                org_id=user.org_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details="Account is inactive/disabled"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        token_data = {
            "sub": user.id,
            "role": user.role.value,
            "org_id": user.org_id,
            "email": user.email,
            "full_name": user.full_name
        }

        # Create short-lived access token
        access_token = create_access_token(token_data)

        # Create secure refresh token and store record
        refresh_token_str, jti, expire_dt = create_refresh_token(token_data)
        refresh_record = RefreshToken(
            user_id=user.id,
            token_jti=jti,
            expires_at=expire_dt,
            is_revoked=False
        )
        db.add(refresh_record)
        db.commit()

        # Generate CSRF token
        csrf_token = generate_csrf_token()

        AuditService.log_event(
            db=db,
            event_type="LOGIN_SUCCESS",
            user_id=user.id,
            email=user.email,
            org_id=user.org_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        token_obj = Token(
            access_token=access_token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            org_id=user.org_id,
            full_name=user.full_name,
            refresh_token=refresh_token_str,
            csrf_token=csrf_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        return token_obj, refresh_token_str, csrf_token

    @staticmethod
    def refresh_access_token(
        db: Session,
        refresh_token_str: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Token, str, str]:
        payload = decode_token(refresh_token_str, expected_type="refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed refresh token"
            )

        # Check DB for token revocation status
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token_jti == jti,
            RefreshToken.user_id == user_id
        ).first()

        if not db_token or db_token.is_revoked:
            AuditService.log_event(
                db=db,
                event_type="REFRESH_TOKEN_REJECTED",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details="Revoked or missing refresh token used"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or is invalid"
            )

        # Verify not expired
        now = datetime.now(timezone.utc)
        token_exp = db_token.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)
        if token_exp < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or not found"
            )

        # Secure Token Rotation: Revoke current refresh token
        db_token.is_revoked = True

        # Issue new token pair
        token_data = {
            "sub": user.id,
            "role": user.role.value,
            "org_id": user.org_id,
            "email": user.email,
            "full_name": user.full_name
        }
        new_access_token = create_access_token(token_data)
        new_refresh_token_str, new_jti, new_expire = create_refresh_token(token_data)

        new_refresh_record = RefreshToken(
            user_id=user.id,
            token_jti=new_jti,
            expires_at=new_expire,
            is_revoked=False
        )
        db.add(new_refresh_record)
        db.commit()

        new_csrf = generate_csrf_token()

        AuditService.log_event(
            db=db,
            event_type="TOKEN_REFRESHED",
            user_id=user.id,
            email=user.email,
            org_id=user.org_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        token_obj = Token(
            access_token=new_access_token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            org_id=user.org_id,
            full_name=user.full_name,
            refresh_token=new_refresh_token_str,
            csrf_token=new_csrf,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        return token_obj, new_refresh_token_str, new_csrf

    @staticmethod
    def logout_user(
        db: Session,
        user_id: str,
        refresh_token_str: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        if refresh_token_str:
            payload = decode_token(refresh_token_str, expected_type="refresh")
            if payload and "jti" in payload:
                db_token = db.query(RefreshToken).filter(
                    RefreshToken.token_jti == payload["jti"]
                ).first()
                if db_token:
                    db_token.is_revoked = True
                    db.commit()

        # Revoke all active refresh tokens for the user
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).update({"is_revoked": True})
        db.commit()

        AuditService.log_event(
            db=db,
            event_type="LOGOUT",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def request_password_reset(
        db: Session,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        email_clean = email.lower().strip()

        reset_key = f"reset:{ip_address or 'unknown'}:{email_clean}"
        allowed, retry_after = AuthRateLimiter.check_rate_limit(reset_key, limit_per_minute=5)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many password reset requests. Please retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

        user = db.query(User).filter(User.email == email_clean).first()

        reset_token_str = generate_reset_token()
        if user and user.is_active:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=reset_token_str,
                expires_at=expires_at,
                is_used=False
            )
            db.add(reset_record)
            db.commit()

            AuditService.log_event(
                db=db,
                event_type="PASSWORD_RESET_REQUESTED",
                user_id=user.id,
                email=user.email,
                org_id=user.org_id,
                ip_address=ip_address,
                user_agent=user_agent
            )

        return {
            "message": "If the email is registered, a password reset link has been dispatched.",
            # Expose token in response for dev/testing environments
            "reset_token": reset_token_str if not settings.is_production else None
        }

    @staticmethod
    def confirm_password_reset(
        db: Session,
        reset_in: PasswordResetConfirm,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        record = db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == reset_in.reset_token,
            PasswordResetToken.is_used == False
        ).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used password reset token"
            )

        now = datetime.now(timezone.utc)
        record_exp = record.expires_at
        if record_exp.tzinfo is None:
            record_exp = record_exp.replace(tzinfo=timezone.utc)
        if record_exp < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has expired"
            )

        user = db.query(User).filter(User.id == record.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account not found or disabled"
            )

        # Update password with Argon2id hash
        user.hashed_password = hash_password(reset_in.new_password)
        record.is_used = True

        # Invalidate all active refresh tokens for the user
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False
        ).update({"is_revoked": True})

        db.commit()

        AuditService.log_event(
            db=db,
            event_type="PASSWORD_RESET_COMPLETED",
            user_id=user.id,
            email=user.email,
            org_id=user.org_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"message": "Password successfully reset. Please log in with your new password."}
