from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models.user import Organization, User, Role
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.utils.security import hash_password
from app.routers import (
    auth_router,
    org_router,
    questions_router,
    assessments_router,
    candidates_router,
    attempts_router,
    proctoring_router,
    sandbox_router,
    coding_router,
    analytics_router,
    ws_router,
    health_router,
    seb_router,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proctorai.main")


def init_db_tables():
    """
    Initializes database schema and tables cleanly.
    """
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting ProctorAI Platform in [{settings.ENVIRONMENT.upper()}] environment...")
    if settings.is_production:
        if settings.SECRET_KEY == "super-secret-production-grade-signing-key-32chars-min!" or len(settings.SECRET_KEY) < 32:
            raise RuntimeError("FATAL: Insecure or default SECRET_KEY cannot be used in production! Set a cryptographically random 32+ character key.")
        logger.info("Production security checks passed: Default demo accounts and mock seeding disabled.")
    
    # Initialize all database tables cleanly (no hardcoded test accounts or mock data)
    init_db_tables()
    yield
    # Shutdown
    logger.info("Shutting down ProctorAI Platform...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers for Consistent Error Handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "status_code": 422,
            "error_type": "validation_error",
            "path": request.url.path,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "A database error occurred while processing the request.",
            "status_code": 500,
            "error_type": "database_error",
            "path": request.url.path,
        },
    )


# Register API routers
app.include_router(health_router)  # /health, /health/live, /health/ready
app.include_router(health_router, prefix=settings.API_V1_STR)  # /api/v1/health...
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(org_router, prefix=settings.API_V1_STR)
app.include_router(questions_router, prefix=settings.API_V1_STR)
app.include_router(assessments_router, prefix=settings.API_V1_STR)
app.include_router(candidates_router, prefix=settings.API_V1_STR)
app.include_router(attempts_router, prefix=settings.API_V1_STR)
app.include_router(proctoring_router, prefix=settings.API_V1_STR)
app.include_router(sandbox_router, prefix=settings.API_V1_STR)
app.include_router(coding_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(seb_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)
app.include_router(ws_router, prefix=settings.API_V1_STR)
