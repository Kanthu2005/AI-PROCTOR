import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "ProctorAI - AI-Powered Assessment & Proctoring Platform"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Logging
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security & Tokens
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-production-grade-signing-key-32chars-min!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))  # 15 minutes short-lived
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))        # 7 days
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "1"))
    INVITATION_TOKEN_EXPIRE_HOURS: int = 72     # 3 days

    # Cookie & CSRF Security
    COOKIE_ACCESS_TOKEN_KEY: str = "proctorai_access_token"
    COOKIE_REFRESH_TOKEN_KEY: str = "proctorai_refresh_token"
    COOKIE_CSRF_TOKEN_KEY: str = "proctorai_csrf_token"
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "True" if os.getenv("ENVIRONMENT", "development").lower() == "production" else "False").lower() in ("true", "1")
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")
    CSRF_PROTECTION_ENABLED: bool = os.getenv("CSRF_PROTECTION_ENABLED", "True").lower() in ("true", "1")
    AUTH_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "10"))
    
    # Dedicated PostgreSQL Configuration (Least-Privilege ProctorAI Database)
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "proctorai_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "proctorai_secure_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "proctorai_db")
    
    # Core Database URL (Defaults to local intellitest.db SQLite if no PostgreSQL URL is provided)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./intellitest.db")
    
    # Database Connection Pool Settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    
    # MongoDB for Telemetry & High-volume proctoring logs
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "proctorai_telemetry")
    
    # Execution Sandbox & Security Boundary
    USE_DOCKER_SANDBOX: bool = os.getenv("USE_DOCKER_SANDBOX", "True").lower() in ("true", "1")
    DOCKER_SANDBOX_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 3
    SANDBOX_MEMORY_LIMIT: str = "128m"
    SANDBOX_MAX_MEMORY_MB: int = int(os.getenv("SANDBOX_MAX_MEMORY_MB", "128"))
    SANDBOX_CPU_QUOTA: int = 50000  # 0.5 CPU
    SANDBOX_PIDS_LIMIT: int = int(os.getenv("SANDBOX_PIDS_LIMIT", "32"))
    SANDBOX_MAX_OUTPUT_BYTES: int = int(os.getenv("SANDBOX_MAX_OUTPUT_BYTES", "65536"))  # 64 KB
    INTERNAL_RUNNER_SECRET: str = os.getenv("INTERNAL_RUNNER_SECRET", "runner-secret-key-proctorai-internal-boundary-auth")
    SANDBOX_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("SANDBOX_RATE_LIMIT_PER_MINUTE", "15"))

    # AI Proctoring & Evidence Retention Settings
    PROCTORING_EVIDENCE_RETENTION_DAYS: int = int(os.getenv("PROCTORING_EVIDENCE_RETENTION_DAYS", "30"))
    PROCTORING_DEDUP_WINDOW_SECONDS: int = int(os.getenv("PROCTORING_DEDUP_WINDOW_SECONDS", "3"))
    PROCTORING_RULE_VERSION: str = "2026.1-explainable"
    
    # CORS (can be list or comma-separated string)
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if not v or v == "*":
                return ["*"]
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["*"]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.lower() == "testing"

    @property
    def postgresql_url_constructed(self) -> str:
        """Constructs dedicated PostgreSQL URL without hardcoding in source code."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
