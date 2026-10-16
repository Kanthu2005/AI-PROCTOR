from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: str
    org_id: Optional[str] = None
    full_name: str
    refresh_token: Optional[str] = None
    csrf_token: Optional[str] = None
    expires_in: Optional[int] = None


class TokenPayload(BaseModel):
    sub: str
    role: Role
    org_id: Optional[str] = None
    exp: Optional[datetime] = None
    type: Optional[str] = "access"
    jti: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=6)


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: Role = Role.CANDIDATE
    org_id: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    org_id: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityAuditResponse(BaseModel):
    id: str
    event_type: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    org_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
