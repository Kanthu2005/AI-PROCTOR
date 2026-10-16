import pytest
from datetime import datetime, timedelta, timezone
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    decode_token,
)
from app.models.user import User, Organization, Role, RefreshToken, PasswordResetToken, SecurityAuditEvent
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.config import settings


def test_argon2id_hashing_and_legacy_verification():
    """Verify passwords are produced with Argon2id and legacy bcrypt hashes still verify."""
    raw_pwd = "SecurePassword123!"
    hashed = hash_password(raw_pwd)
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

    # Legacy bcrypt hash verification check
    import bcrypt
    legacy_bcrypt_hash = bcrypt.hashpw(raw_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    assert legacy_bcrypt_hash.startswith("$2")
    assert verify_password(raw_pwd, legacy_bcrypt_hash) is True
    assert verify_password("WrongPassword!", legacy_bcrypt_hash) is False


def test_login_success_and_cookie_generation(client, db, test_org):
    """Test login sets tokens and HttpOnly cookies and logs LOGIN_SUCCESS."""
    user = User(
        email="login_success@test.com",
        hashed_password=hash_password("MyPassword123!"),
        full_name="Success User",
        role=Role.RECRUITER,
        org_id=test_org.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/v1/auth/login", json={
        "email": "login_success@test.com",
        "password": "MyPassword123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user_id"] == user.id
    assert data["role"] == "RECRUITER"
    assert data["full_name"] == "Success User"

    # Verify cookies
    assert settings.COOKIE_ACCESS_TOKEN_KEY in resp.cookies
    assert settings.COOKIE_REFRESH_TOKEN_KEY in resp.cookies
    assert settings.COOKIE_CSRF_TOKEN_KEY in resp.cookies

    # Verify audit event
    audit = db.query(SecurityAuditEvent).filter(
        SecurityAuditEvent.user_id == user.id,
        SecurityAuditEvent.event_type == "LOGIN_SUCCESS"
    ).first()
    assert audit is not None


def test_login_invalid_credentials_logs_audit(client, db, test_org):
    """Test invalid credentials returns 401 and logs LOGIN_FAILED."""
    user = User(
        email="target@test.com",
        hashed_password=hash_password("RealPassword123!"),
        full_name="Target User",
        role=Role.CANDIDATE,
        org_id=test_org.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/v1/auth/login", json={
        "email": "target@test.com",
        "password": "BadPassword999!"
    })
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]

    audit = db.query(SecurityAuditEvent).filter(
        SecurityAuditEvent.event_type == "LOGIN_FAILED",
        SecurityAuditEvent.email == "target@test.com"
    ).first()
    assert audit is not None


def test_login_inactive_user_rejected(client, db, test_org):
    """Test inactive account cannot login."""
    user = User(
        email="inactive@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Inactive User",
        role=Role.CANDIDATE,
        org_id=test_org.id,
        is_active=False,
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/v1/auth/login", json={
        "email": "inactive@test.com",
        "password": "Pass123!"
    })
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()


def test_current_user_me_endpoint_bearer_and_cookie(client, proctor, proctor_headers):
    """Test /auth/me returns current user profile using Bearer header or Cookie."""
    # 1. Bearer header
    resp = client.get("/api/v1/auth/me", headers=proctor_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == proctor.email
    assert resp.json()["role"] == "PROCTOR"

    # 2. Cookie authentication
    token = proctor_headers["Authorization"].split(" ")[1]
    client.cookies.set(settings.COOKIE_ACCESS_TOKEN_KEY, token)
    resp_cookie = client.get("/api/v1/auth/me")
    assert resp_cookie.status_code == 200
    assert resp_cookie.json()["id"] == proctor.id
    client.cookies.clear()


def test_expired_access_token_rejected(client, recruiter):
    """Test that expired access tokens are rejected with 401."""
    expired_token = create_access_token(
        data={"sub": recruiter.id, "role": recruiter.role.value, "org_id": recruiter.org_id},
        expires_delta=timedelta(seconds=-10)
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_refresh_token_rotation(client, db, org_admin):
    """Test refresh token rotation: old refresh token revoked, new tokens issued."""
    # First login to obtain tokens
    login_resp = client.post("/api/v1/auth/login", json={
        "email": org_admin.email,
        "password": "Pass123!"
    })
    assert login_resp.status_code == 200
    old_refresh_token = login_resp.json()["refresh_token"]

    # Decode old token to extract jti
    old_payload = decode_token(old_refresh_token, expected_type="refresh")
    assert old_payload is not None
    old_jti = old_payload["jti"]

    # Call /refresh with the refresh token
    refresh_resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": old_refresh_token
    })
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    new_refresh_token = new_data["refresh_token"]
    assert new_refresh_token != old_refresh_token
    assert "access_token" in new_data

    # Verify the old refresh token record in DB is revoked
    old_record = db.query(RefreshToken).filter(RefreshToken.token_jti == old_jti).first()
    assert old_record is not None
    assert old_record.is_revoked is True

    # Attempting to use the revoked old refresh token must be rejected
    reuse_resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": old_refresh_token
    })
    assert reuse_resp.status_code == 401


def test_logout_revokes_tokens_and_clears_cookies(client, db, proctor):
    """Test logout invalidates active refresh tokens, clears cookies, and logs LOGOUT."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": proctor.email,
        "password": "Pass123!"
    })
    access_token = login_resp.json()["access_token"]
    csrf_token = login_resp.cookies.get(settings.COOKIE_CSRF_TOKEN_KEY)

    # Set cookies on client
    client.cookies.set(settings.COOKIE_ACCESS_TOKEN_KEY, access_token)
    client.cookies.set(settings.COOKIE_CSRF_TOKEN_KEY, csrf_token)

    logout_resp = client.post("/api/v1/auth/logout", headers={
        "Authorization": f"Bearer {access_token}",
        "X-CSRF-Token": csrf_token
    })
    assert logout_resp.status_code == 200

    # Ensure all refresh tokens for this user are revoked
    active_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == proctor.id,
        RefreshToken.is_revoked == False
    ).all()
    assert len(active_tokens) == 0

    # Check LOGOUT audit event
    audit = db.query(SecurityAuditEvent).filter(
        SecurityAuditEvent.user_id == proctor.id,
        SecurityAuditEvent.event_type == "LOGOUT"
    ).first()
    assert audit is not None


def test_password_reset_flow(client, db, test_org):
    """Test full password reset request and confirm lifecycle with Argon2id update."""
    user = User(
        email="reset_user@test.com",
        hashed_password=hash_password("OldPassword123!"),
        full_name="Reset User",
        role=Role.CANDIDATE,
        org_id=test_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()

    # Step 1: Request password reset
    req_resp = client.post("/api/v1/auth/password-reset/request", json={
        "email": "reset_user@test.com"
    })
    assert req_resp.status_code == 200
    reset_data = req_resp.json()
    reset_token = reset_data.get("reset_token")
    assert reset_token is not None

    # Verify audit event for request
    req_audit = db.query(SecurityAuditEvent).filter(
        SecurityAuditEvent.user_id == user.id,
        SecurityAuditEvent.event_type == "PASSWORD_RESET_REQUESTED"
    ).first()
    assert req_audit is not None

    # Step 2: Confirm password reset with new password
    new_pwd = "BrandNewPassword2026!"
    confirm_resp = client.post("/api/v1/auth/password-reset/confirm", json={
        "reset_token": reset_token,
        "new_password": new_pwd
    })
    assert confirm_resp.status_code == 200

    # Verify user password is updated and stored with Argon2id
    db.refresh(user)
    assert user.hashed_password.startswith("$argon2id$")
    assert verify_password(new_pwd, user.hashed_password) is True

    # Old password no longer works
    assert client.post("/api/v1/auth/login", json={
        "email": "reset_user@test.com",
        "password": "OldPassword123!"
    }).status_code == 401

    # New password works for login
    assert client.post("/api/v1/auth/login", json={
        "email": "reset_user@test.com",
        "password": new_pwd
    }).status_code == 200

    # Step 3: Reusing the same reset token must fail
    reuse_confirm = client.post("/api/v1/auth/password-reset/confirm", json={
        "reset_token": reset_token,
        "new_password": "YetAnotherPassword123!"
    })
    assert reuse_confirm.status_code == 400


def test_csrf_protection_on_cookie_authenticated_mutation(client, proctor):
    """Mutating cookie requests without valid X-CSRF-Token header are rejected with 403."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": proctor.email,
        "password": "Pass123!"
    })
    access_token = login_resp.json()["access_token"]
    csrf_cookie = login_resp.cookies.get(settings.COOKIE_CSRF_TOKEN_KEY)

    client.cookies.set(settings.COOKIE_ACCESS_TOKEN_KEY, access_token)
    client.cookies.set(settings.COOKIE_CSRF_TOKEN_KEY, csrf_cookie)

    # 1. Mutating POST without X-CSRF-Token header must return 403
    resp_no_csrf = client.post("/api/v1/auth/logout")
    assert resp_no_csrf.status_code == 403
    assert "CSRF" in resp_no_csrf.json()["detail"]

    # 2. Mutating POST with mismatched X-CSRF-Token header must return 403
    resp_bad_csrf = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "invalid_forged_csrf_token"})
    assert resp_bad_csrf.status_code == 403

    # 3. Mutating POST with correct X-CSRF-Token succeeds
    resp_good_csrf = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_cookie})
    assert resp_good_csrf.status_code == 200
    client.cookies.clear()


def test_cross_tenant_isolation_blocked_and_audited(client, db, recruiter, recruiter_headers):
    """Users cannot access resources from other organizations (IDOR prevention)."""
    # Create Organization B
    org_b = Organization(name="Other Corp", slug="othercorp", domain="other.com", is_active=True)
    db.add(org_b)
    db.commit()

    # Recruiter belongs to test_org (Org A) and attempts to access org_b
    resp = client.get(f"/api/v1/organizations/{org_b.id}", headers=recruiter_headers)
    assert resp.status_code == 403
    assert "another organization" in resp.json()["detail"].lower()

    # Recruiter attempts to access candidates query filtered by org_b
    cand_resp = client.get(f"/api/v1/candidates?org_id={org_b.id}", headers=recruiter_headers)
    assert cand_resp.status_code == 403

    # Verify CROSS_TENANT_ACCESS_BLOCKED audit event was recorded
    audit = db.query(SecurityAuditEvent).filter(
        SecurityAuditEvent.user_id == recruiter.id,
        SecurityAuditEvent.event_type == "CROSS_TENANT_ACCESS_BLOCKED"
    ).first()
    assert audit is not None


def test_platform_admin_can_access_across_tenants(client, db, platform_admin_headers):
    """Platform Admin role has global administrative rights and can access resources across tenants."""
    org_b = Organization(name="Tenant Beta", slug="tenantbeta", domain="beta.com", is_active=True)
    db.add(org_b)
    db.commit()

    resp = client.get(f"/api/v1/organizations/{org_b.id}", headers=platform_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Tenant Beta"


def test_rbac_candidate_cannot_access_recruiter_endpoints(client, candidate_headers):
    """Candidate role cannot access recruiter/admin endpoints."""
    # Attempting to list all candidates
    resp = client.get("/api/v1/candidates", headers=candidate_headers)
    assert resp.status_code == 403
    assert "access forbidden" in resp.json()["detail"].lower()


def test_security_audit_logs_role_authorization(client, db, org_admin, org_admin_headers, candidate_headers):
    """Security audit logs are accessible to Org/Platform Admin and denied to Candidates."""
    # Org admin can view audit logs
    resp_admin = client.get("/api/v1/auth/audit-logs", headers=org_admin_headers)
    assert resp_admin.status_code == 200
    assert isinstance(resp_admin.json(), list)

    # Candidate is forbidden
    resp_cand = client.get("/api/v1/auth/audit-logs", headers=candidate_headers)
    assert resp_cand.status_code == 403
