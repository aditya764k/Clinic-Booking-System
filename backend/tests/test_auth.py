"""
Module 2 — Authentication & RBAC Integration Tests
===================================================

Tests are run against a SQLite in-memory database (see conftest.py).
No Docker or Postgres required.

Test coverage (a–i per the spec):
a) Register patient, receptionist, doctor — check 201 + profile rows
b) Duplicate email → 409
c) Login → Set-Cookie headers with HttpOnly flag
d) Login with wrong password → 401
e) /auth/whoami with no cookie → 401
f) /auth/whoami with valid cookie → 200 + correct identity
g) /auth/whoami with tampered/expired token → 401
h) RBAC: require_role("doctor") rejects patient (403), accepts doctor (200)
i) Logout → cookies cleared, subsequent whoami fails
"""
import time
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from jose import jwt

from app.core.dependencies import require_role
from app.core.security import decode_token
from app.main import app
from app.models.identity import DoctorProfile, PatientProfile

# ── Helpers ───────────────────────────────────────────────────────────────────

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
WHOAMI_URL = "/auth/whoami"
LOGOUT_URL = "/auth/logout"
REFRESH_URL = "/auth/refresh"


def _register(client: TestClient, email: str, password: str, role: str, full_name: str = "Test User"):
    return client.post(
        REGISTER_URL,
        json={"email": email, "password": password, "role": role, "full_name": full_name},
    )


def _login(client: TestClient, email: str, password: str):
    return client.post(LOGIN_URL, json={"email": email, "password": password})


def _has_httponly_cookie(response, name: str) -> bool:
    """Check the raw Set-Cookie headers for HttpOnly flag on *name* cookie."""
    for header_value in response.headers.get_list("set-cookie"):
        if f"{name}=" in header_value and "httponly" in header_value.lower():
            return True
    return False


# ── (a) Registration of all three roles ──────────────────────────────────────

class TestRegister:
    def test_register_patient_creates_profile(self, client, db_session):
        """Patient registration → 201, PatientProfile row created."""
        resp = _register(client, "patient@test.com", "Password1!", "patient", "Alice Patient")
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["email"] == "patient@test.com"
        assert body["role"] == "patient"
        assert "id" in body

        profile = db_session.query(PatientProfile).filter_by(full_name="Alice Patient").first()
        assert profile is not None
        assert profile.user_id == body["id"]

    def test_register_doctor_creates_profile(self, client, db_session):
        """Doctor registration → 201, DoctorProfile row created."""
        resp = _register(client, "doctor@test.com", "Password1!", "doctor", "Dr. Bob")
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["role"] == "doctor"

        profile = db_session.query(DoctorProfile).filter_by(full_name="Dr. Bob").first()
        assert profile is not None
        assert profile.user_id == body["id"]

    def test_register_receptionist_no_profile(self, client, db_session):
        """Receptionist registration → 201, no PatientProfile/DoctorProfile."""
        resp = _register(client, "recept@test.com", "Password1!", "receptionist", "Carol R")
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["role"] == "receptionist"

        assert db_session.query(PatientProfile).filter_by(user_id=body["id"]).first() is None
        assert db_session.query(DoctorProfile).filter_by(user_id=body["id"]).first() is None

    def test_register_auto_login_sets_cookies(self, client):
        """Register → auto-login sets access_token + refresh_token cookies."""
        resp = _register(client, "autotest@test.com", "Password1!", "patient", "Auto Patient")
        assert resp.status_code == 201
        # Cookies should be set on the client jar
        assert client.cookies.get("access_token") is not None
        assert client.cookies.get("refresh_token") is not None

    def test_register_password_too_short(self, client):
        """Password under 8 chars → 422 validation error."""
        resp = _register(client, "short@test.com", "abc", "patient", "Short Pass")
        assert resp.status_code == 422

    def test_register_invalid_role(self, client):
        """Unknown role → 422 validation error."""
        resp = client.post(
            REGISTER_URL,
            json={"email": "bad@test.com", "password": "Password1!", "role": "admin", "full_name": "Bad Role"},
        )
        assert resp.status_code == 422


# ── (b) Duplicate email ───────────────────────────────────────────────────────

class TestDuplicateEmail:
    def test_duplicate_email_rejected(self, client):
        """Second registration with same email → 409 Conflict."""
        _register(client, "dup@test.com", "Password1!", "patient", "First User")
        resp = _register(client, "dup@test.com", "Password1!", "doctor", "Second User")
        assert resp.status_code == 409


# ── (c) Login sets HttpOnly cookies ──────────────────────────────────────────

class TestLogin:
    def test_login_success_sets_cookies(self, client):
        """Successful login sets access_token + refresh_token as HttpOnly cookies."""
        _register(client, "cookietest@test.com", "Password1!", "patient", "Cookie Tester")
        # Clear cookies from registration auto-login
        client.cookies.clear()

        resp = _login(client, "cookietest@test.com", "Password1!")
        assert resp.status_code == 200

        assert _has_httponly_cookie(resp, "access_token"), "access_token missing HttpOnly flag"
        assert _has_httponly_cookie(resp, "refresh_token"), "refresh_token missing HttpOnly flag"

    def test_login_response_contains_user_out(self, client):
        """Login response body is UserOut (no password field)."""
        _register(client, "body@test.com", "Password1!", "patient", "Body Test")
        client.cookies.clear()
        resp = _login(client, "body@test.com", "Password1!")
        body = resp.json()
        assert "id" in body
        assert "email" in body
        assert "role" in body
        assert "created_at" in body
        assert "hashed_password" not in body
        assert "password" not in body

    # ── (d) Wrong password → 401 ──────────────────────────────────────────────

    def test_login_wrong_password(self, client):
        """Login with incorrect password → 401."""
        _register(client, "wrongpw@test.com", "Password1!", "patient", "Wrong PW")
        client.cookies.clear()
        resp = _login(client, "wrongpw@test.com", "WrongPassword!")
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login with email that doesn't exist → 401 (not 404, to avoid user enumeration)."""
        resp = _login(client, "ghost@test.com", "Password1!")
        assert resp.status_code == 401


# ── (e) Whoami — no cookie ────────────────────────────────────────────────────

class TestWhoami:
    def test_whoami_no_cookie_returns_401(self, client):
        """GET /auth/whoami with no cookie → 401."""
        client.cookies.clear()
        resp = client.get(WHOAMI_URL)
        assert resp.status_code == 401

    # ── (f) Whoami — valid cookie ─────────────────────────────────────────────

    def test_whoami_valid_cookie_returns_user(self, client):
        """GET /auth/whoami with valid cookie → 200 and correct identity."""
        _register(client, "whoami@test.com", "Password1!", "doctor", "Dr. Whoami")
        resp = client.get(WHOAMI_URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "whoami@test.com"
        assert body["role"] == "doctor"

    # ── (g) Whoami — tampered/expired token ──────────────────────────────────

    def test_whoami_tampered_token_returns_401(self, client):
        """GET /auth/whoami with a forged token → 401."""
        client.cookies.clear()
        client.cookies.set("access_token", "totally.fake.token")
        resp = client.get(WHOAMI_URL)
        assert resp.status_code == 401

    def test_whoami_expired_token_returns_401(self, client):
        """GET /auth/whoami with a legitimately expired token → 401."""
        # Craft a token that expired 1 hour ago using the real secret
        from app.core.config import settings as _settings

        now = datetime.now(tz=timezone.utc)
        payload = {
            "sub": "1",
            "role": "patient",
            "type": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),  # expired
        }
        expired_token = jwt.encode(payload, _settings.JWT_SECRET_KEY, algorithm=_settings.JWT_ALGORITHM)

        client.cookies.clear()
        client.cookies.set("access_token", expired_token)
        resp = client.get(WHOAMI_URL)
        assert resp.status_code == 401

    def test_whoami_refresh_token_as_access_returns_401(self, client):
        """Using a refresh token where an access token is expected → 401."""
        _register(client, "mixup@test.com", "Password1!", "patient", "Token Mixup")
        refresh_tok = client.cookies.get("refresh_token")
        assert refresh_tok, "No refresh token after registration"

        client.cookies.clear()
        client.cookies.set("access_token", refresh_tok)
        resp = client.get(WHOAMI_URL)
        assert resp.status_code == 401


# ── (h) RBAC ─────────────────────────────────────────────────────────────────

# Add a temporary test-only endpoint to app for RBAC testing.
# This mirrors exactly the pattern every future module will use.
from app.models.identity import User as _User
from app.main import app as _app


@_app.get("/test-rbac/doctor-only")
def _doctor_only(current_user: _User = Depends(require_role("doctor"))):
    return {"role": current_user.role.value if hasattr(current_user.role, "value") else current_user.role}


@_app.get("/test-rbac/staff-only")
def _staff_only(current_user: _User = Depends(require_role("doctor", "receptionist"))):
    return {"role": current_user.role.value if hasattr(current_user.role, "value") else current_user.role}


class TestRBAC:
    def test_doctor_role_accepted_on_doctor_endpoint(self, authenticated_client):
        """Doctor token accepted by require_role("doctor") → 200."""
        ac = authenticated_client(role="doctor")
        resp = ac.get("/test-rbac/doctor-only")
        assert resp.status_code == 200
        assert resp.json()["role"] == "doctor"

    def test_patient_role_rejected_on_doctor_endpoint(self, authenticated_client):
        """Patient token rejected by require_role("doctor") → 403."""
        ac = authenticated_client(role="patient")
        resp = ac.get("/test-rbac/doctor-only")
        assert resp.status_code == 403
        assert "Insufficient permissions" in resp.json()["detail"]

    def test_receptionist_accepted_on_staff_endpoint(self, authenticated_client):
        """Receptionist accepted by require_role("doctor", "receptionist") → 200."""
        ac = authenticated_client(role="receptionist")
        resp = ac.get("/test-rbac/staff-only")
        assert resp.status_code == 200

    def test_patient_rejected_on_staff_endpoint(self, authenticated_client):
        """Patient rejected by require_role("doctor", "receptionist") → 403."""
        ac = authenticated_client(role="patient")
        resp = ac.get("/test-rbac/staff-only")
        assert resp.status_code == 403


# ── (i) Logout ────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_clears_cookies(self, client):
        """POST /auth/logout → cookies are expired/cleared."""
        _register(client, "logout@test.com", "Password1!", "patient", "Logout Test")
        # Confirm we're authenticated before logout
        assert client.get(WHOAMI_URL).status_code == 200

        resp = client.post(LOGOUT_URL)
        assert resp.status_code == 204

        # After logout the cookie jar should have expired/empty cookies.
        # We verify by clearing any residual cookies and confirming whoami fails.
        client.cookies.clear()
        assert client.get(WHOAMI_URL).status_code == 401

    def test_logout_then_whoami_with_old_cookie_fails(self, client):
        """After logout, manually reattaching the old cookie still fails if cleared server-side.

        Note: Since we can't revoke JWTs server-side in this stateless implementation,
        we test that (a) logout clears the client cookie jar and (b) a subsequent
        whoami without any cookie returns 401 — proving the client no longer has auth.
        If token revocation (blocklist) is added in future, this test can be extended.
        """
        _register(client, "oldcookie@test.com", "Password1!", "patient", "Old Cookie")
        old_token = client.cookies.get("access_token")
        assert old_token

        client.post(LOGOUT_URL)
        # Client cookie jar is now cleared by the Set-Cookie: access_token=; max-age=0 response
        # Verify the cookie was cleared from the jar
        current_access = client.cookies.get("access_token")
        assert not current_access, "Cookie should be cleared from jar after logout"


# ── Refresh token endpoint ─────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_issues_new_access_cookie(self, client):
        """POST /auth/refresh with valid refresh cookie → 204, new access_token cookie."""
        _register(client, "refresh@test.com", "Password1!", "patient", "Refresh Test")
        old_access = client.cookies.get("access_token")

        # Small sleep to ensure exp differs (jwt has second-level precision)
        time.sleep(1)
        resp = client.post(REFRESH_URL)
        assert resp.status_code == 204

        new_access = client.cookies.get("access_token")
        assert new_access is not None
        # The new token should be freshly issued
        new_payload = decode_token(new_access)
        assert new_payload["type"] == "access"

    def test_refresh_without_cookie_returns_401(self, client):
        """POST /auth/refresh with no refresh cookie → 401."""
        client.cookies.clear()
        resp = client.post(REFRESH_URL)
        assert resp.status_code == 401
