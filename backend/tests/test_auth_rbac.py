import pytest
from app.models.user import Role


def test_user_registration_success(client, test_org):
    payload = {
        "email": "new_recruiter@testcorp.com",
        "password": "Password123!",
        "full_name": "New Recruiter",
        "role": "RECRUITER",
        "org_id": test_org.id
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_recruiter@testcorp.com"
    assert data["role"] == "RECRUITER"
    assert "id" in data


def test_duplicate_email_registration_rejected(client, test_org):
    payload = {
        "email": "duplicate@testcorp.com",
        "password": "Password123!",
        "full_name": "Original User",
        "role": "CANDIDATE",
        "org_id": test_org.id
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_login_valid_credentials_success(client, recruiter):
    payload = {
        "email": recruiter.email,
        "password": "Pass123!"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == Role.RECRUITER.value


def test_login_invalid_password_returns_401(client, recruiter):
    payload = {
        "email": recruiter.email,
        "password": "WrongPassword!"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_inactive_user_cannot_login(client, db, test_org):
    from app.models.user import User
    from app.utils.security import hash_password
    inactive_user = User(
        email="inactive@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Inactive User",
        role=Role.CANDIDATE,
        org_id=test_org.id,
        is_active=False
    )
    db.add(inactive_user)
    db.commit()

    response = client.post("/api/v1/auth/login", json={
        "email": "inactive@test.com",
        "password": "Pass123!"
    })
    assert response.status_code == 403
    assert "Account is disabled" in response.json()["detail"]


def test_platform_admin_can_create_organization(client, platform_admin_headers):
    payload = {
        "name": "Global Tech",
        "slug": "globaltech",
        "domain": "globaltech.io"
    }
    response = client.post("/api/v1/organizations", json=payload, headers=platform_admin_headers)
    assert response.status_code == 201
    assert response.json()["slug"] == "globaltech"


def test_candidate_forbidden_from_admin_actions(client, candidate_headers):
    # Candidate attempting to create organization
    payload = {"name": "Illegal Org", "slug": "illegal"}
    response = client.post("/api/v1/organizations", json=payload, headers=candidate_headers)
    assert response.status_code == 403

    # Candidate attempting to create question
    q_payload = {
        "org_id": "any",
        "title": "Hack Q",
        "description": "desc",
        "question_type": "MCQ_SINGLE"
    }
    response_q = client.post("/api/v1/questions", json=q_payload, headers=candidate_headers)
    assert response_q.status_code == 403


def test_get_me_returns_current_authenticated_profile(client, proctor, proctor_headers):
    response = client.get("/api/v1/auth/me", headers=proctor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == proctor.id
    assert data["email"] == proctor.email
    assert data["role"] in ("PROCTOR", "RECRUITER")

