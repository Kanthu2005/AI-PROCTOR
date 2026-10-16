from app.routers.auth import router as auth_router
from app.routers.organizations import router as org_router
from app.routers.questions import router as questions_router
from app.routers.assessments import router as assessments_router
from app.routers.candidates import router as candidates_router
from app.routers.attempts import router as attempts_router
from app.routers.proctoring import router as proctoring_router
from app.routers.sandbox import router as sandbox_router
from app.routers.analytics import router as analytics_router
from app.routers.ws import router as ws_router
from app.routers.coding import router as coding_router
from app.routers.health import router as health_router
from app.routers.seb import router as seb_router

__all__ = [
    "auth_router",
    "org_router",
    "questions_router",
    "assessments_router",
    "candidates_router",
    "attempts_router",
    "proctoring_router",
    "sandbox_router",
    "coding_router",
    "analytics_router",
    "ws_router",
    "health_router",
    "seb_router",
]
