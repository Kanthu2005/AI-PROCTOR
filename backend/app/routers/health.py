import time
from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.config import settings
from app.database import check_db_connection

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health", summary="Service Liveness Probe")
@router.get("/health/live", summary="Service Liveness Check")
def liveness_check():
    """
    Returns basic service liveness status.
    Fast, non-blocking check used by load balancers and orchestrators.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/ready", summary="Service Readiness Probe")
def readiness_check(response: Response):
    """
    Returns service readiness by validating database connectivity and sandbox configuration.
    Returns HTTP 200 if ready to serve traffic, HTTP 503 if database is disconnected.
    """
    start = time.perf_counter()
    db_check = check_db_connection()
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    is_ready = db_check.get("connected", False)

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        service_status = "unhealthy"
    else:
        service_status = "healthy"

    return {
        "status": service_status,
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": db_check.get("status", "unknown"),
        "database_dialect": db_check.get("dialect", "unknown"),
        "database_latency_ms": latency_ms,
        "database_connected": is_ready,
        "database_details": {
            "status": db_check.get("status", "unknown"),
            "dialect": db_check.get("dialect", "unknown"),
            "latency_ms": latency_ms,
            "connected": is_ready
        },
        "sandbox": {
            "type": "docker" if settings.USE_DOCKER_SANDBOX else "subprocess_isolated",
            "timeout_seconds": settings.SANDBOX_TIMEOUT_SECONDS,
            "memory_limit": settings.SANDBOX_MEMORY_LIMIT
        },
        "ready": is_ready,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
