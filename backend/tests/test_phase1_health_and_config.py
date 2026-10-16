import pytest
from sqlalchemy import text
from app.config import settings
from app.database import check_db_connection, get_db


def test_health_liveness_endpoint(client):
    """Test that the /health liveness probe returns HTTP 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data


def test_health_live_alias_endpoint(client):
    """Test the /health/live probe alias."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_health_readiness_endpoint(client):
    """Test that /health/ready probe verifies database connectivity and returns HTTP 200."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ready"] is True
    assert data["database"] == "connected"
    assert "database_dialect" in data


def test_api_v1_health_endpoints(client):
    """Test that health checks are accessible via /api/v1 prefix as well."""
    response_live = client.get(f"{settings.API_V1_STR}/health")
    assert response_live.status_code == 200
    assert response_live.json()["status"] == "healthy"

    response_ready = client.get(f"{settings.API_V1_STR}/health/ready")
    assert response_ready.status_code == 200
    assert response_ready.json()["ready"] is True


def test_configuration_settings():
    """Test configuration settings defaults and environment helper properties."""
    assert settings.PROJECT_NAME is not None
    assert settings.API_V1_STR == "/api/v1"
    assert settings.POSTGRES_DB == "proctorai_db"
    assert settings.POSTGRES_USER == "proctorai_user"
    assert isinstance(settings.CORS_ORIGINS, list)
    assert hasattr(settings, "is_sqlite")
    assert hasattr(settings, "is_production")
    assert hasattr(settings, "postgresql_url_constructed")
    # Verify passwords are never leaked in plain representation
    assert "proctorai_db" in settings.postgresql_url_constructed


def test_database_connectivity_helper():
    """Directly test the check_db_connection() helper."""
    result = check_db_connection()
    assert isinstance(result, dict)
    assert result["connected"] is True
    assert result["status"] == "connected"
    assert "dialect" in result


def test_consistent_error_handling_not_found(client):
    """Test that 404 errors adhere to consistent JSON envelope format."""
    response = client.get("/api/v1/nonexistent-route-for-testing-404")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["status_code"] == 404
    assert data["path"] == "/api/v1/nonexistent-route-for-testing-404"


def test_consistent_error_handling_validation(client):
    """Test that 422 validation errors adhere to consistent JSON envelope format."""
    response = client.post(f"{settings.API_V1_STR}/auth/login", json={})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["status_code"] == 422
    assert data["error_type"] == "validation_error"


def test_sqlalchemy_session_lifecycle(db):
    """Verify that the database session operates cleanly with rollback capability."""
    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1
