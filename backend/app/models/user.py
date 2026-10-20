import enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Role(str, enum.Enum):
    ADMIN_RECRUITER = "ADMIN_RECRUITER"
    CANDIDATE = "CANDIDATE"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    
    # Backwards-compatible legacy roles mapped into ADMIN_RECRUITER
    ORG_ADMIN = "ORG_ADMIN"
    RECRUITER = "RECRUITER"
    QUESTION_AUTHOR = "QUESTION_AUTHOR"
    PROCTOR = "PROCTOR"

    @classmethod
    def normalize(cls, role_val: str) -> "Role":
        if isinstance(role_val, cls):
            return role_val
        val = str(role_val).upper()
        if val in ("RECRUITER", "ORG_ADMIN", "QUESTION_AUTHOR", "PROCTOR", "ADMIN_RECRUITER"):
            return cls.ADMIN_RECRUITER
        if val == "PLATFORM_ADMIN":
            return cls.PLATFORM_ADMIN
        return cls.CANDIDATE


class Organization(BaseModel):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    domain = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="organization", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="organization", cascade="all, delete-orphan")


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(Role), default=Role.CANDIDATE, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    organization = relationship("Organization", back_populates="users")

    # Relationships
    authored_questions = relationship("QuestionVersion", back_populates="author")
    authored_assessments = relationship("Assessment", back_populates="creator")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(BaseModel):
    __tablename__ = "password_reset_tokens"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")


class SecurityAuditEvent(BaseModel):
    __tablename__ = "security_audit_events"

    event_type = Column(String(64), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    org_id = Column(String(36), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
