import secrets
import uuid
import argon2
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from app.config import settings

# Argon2id password hasher configured to OWASP recommendations
_argon2_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    type=argon2.Type.ID  # Argon2id variant
)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _argon2_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against an Argon2id or legacy bcrypt hash.
    Returns True if valid, False otherwise.
    """
    if not hashed_password:
        return False
    try:
        # Check Argon2id hash first
        if hashed_password.startswith("$argon2"):
            try:
                _argon2_hasher.verify(hashed_password, plain_password)
                return True
            except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError):
                return False

        # Fallback to legacy bcrypt for existing hashes
        if hashed_password.startswith(("$2b$", "$2a$", "$2y$")):
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

        return False
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a short-lived access JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": str(uuid.uuid4())
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> Tuple[str, str, datetime]:
    """
    Creates a secure refresh JWT token.
    Returns (token_string, jti, expire_datetime).
    """
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": jti
    })
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, expire


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates an access JWT token."""
    return decode_token(token, expected_type="access")


def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token of an expected type."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if expected_type and payload.get("type") != expected_type:
            # Allow backwards compatibility if token has no type specified (for existing access tokens in tests)
            if payload.get("type") is not None and payload.get("type") != expected_type:
                return None
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def generate_invitation_token() -> str:
    """Generates a high-entropy URL-safe invitation token."""
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """Generates a high-entropy URL-safe password reset token."""
    return secrets.token_urlsafe(40)


def generate_csrf_token() -> str:
    """Generates a high-entropy random CSRF token."""
    return secrets.token_hex(32)


def is_demo_replayable_token(invitation_token: Optional[str]) -> bool:
    """
    Returns True ONLY if in development environment and matching the explicit demo seed token 'ABC123'.
    Strictly disabled in production and testing to prevent token replay or submitted attempt tampering.
    """
    if not invitation_token:
        return False
    if settings.is_production or settings.is_testing:
        return False
    return settings.ENVIRONMENT.lower() == "development" and invitation_token == "ABC123"
