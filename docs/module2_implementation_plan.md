# Module 2: Authentication & RBAC Implementation Plan

## Overview

Build the complete auth layer (HttpOnly cookie JWTs, password hashing, Google SSO, RBAC dependency factory) on top of the already-migrated Module 1 schema. No Module 1 model changes are needed — the `User`, `PatientProfile`, `DoctorProfile` tables already have all required columns (`hashed_password`, `google_sub`, `role`).

**Auto-login decision**: `POST /auth/register` will auto-login the user (issue cookies immediately on registration) for smoother UX — no second round-trip needed.

---

## Proposed Changes

### 1. Dependencies & Config

#### [MODIFY] requirements.txt
- `passlib[bcrypt]` and `python-jose[cryptography]` already present ✅
- Add: `authlib>=1.3.0`, `httpx>=0.27.0` (authlib needs httpx for async OAuth), `python-multipart` (for form data if needed)

#### [NEW] app/core/config.py
Pydantic-settings `Settings` class with all required env vars:
- `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default HS256), `JWT_EXPIRE_MINUTES` (default 60), `JWT_REFRESH_EXPIRE_DAYS` (default 7)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `COOKIE_SECURE` (bool, default True), `FRONTEND_ORIGIN` (default `http://localhost:3000`)

#### [MODIFY] .env
Add missing keys: `JWT_EXPIRE_MINUTES`, `JWT_REFRESH_EXPIRE_DAYS`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `COOKIE_SECURE=false`, `FRONTEND_ORIGIN`

---

### 2. Core Security

#### [NEW] app/core/security.py
- `CryptContext` with bcrypt scheme
- `hash_password(plain)` / `verify_password(plain, hashed)` 
- `create_access_token(user_id, role)` — payload: `sub`, `role`, `exp`, `iat`, `type="access"`
- `create_refresh_token(user_id)` — payload: `sub`, `exp`, `type="refresh"`
- `decode_token(token)` — raises `TokenExpiredError`, `InvalidTokenError` with clear messages

---

### 3. Auth Schemas

#### [NEW] app/schemas/auth.py
- `RegisterRequest`: email (EmailStr), password (min 8 chars), role (Literal["patient","receptionist","doctor"]), full_name
- `LoginRequest`: email, password
- `UserOut`: id, email, role, created_at (Config: `from_attributes=True`)

---

### 4. Auth Dependencies

#### [NEW] app/core/dependencies.py
- `get_current_user(request: Request, db: Session = Depends(get_db))`: reads `access_token` cookie → decodes → DB lookup → returns `User`
- `require_role(*allowed_roles)`: factory that returns a FastAPI dependency wrapping `get_current_user` + role check

---

### 5. Auth Router

#### [NEW] app/api/auth.py
All endpoints on router with prefix `/auth`:

| Method | Path | Description |
|--------|------|-------------|
| POST | /register | Create user + profile, auto-login (set cookies), return UserOut |
| POST | /login | Verify creds, set cookies, return UserOut |
| POST | /refresh | Read refresh cookie, issue new access cookie |
| POST | /logout | Clear both cookies |
| GET | /whoami | Protected by `get_current_user`, return UserOut |
| GET | /google/login | Redirect to Google OAuth consent |
| GET | /google/callback | Handle OAuth callback, set cookies, redirect to frontend |

Cookie settings for all token cookies:
- `httponly=True`, `secure=settings.COOKIE_SECURE`, `samesite="strict"`

---

### 6. Main App Update

#### [MODIFY] app/main.py
- Import and include `auth_router` with prefix `/auth`
- Update CORS to use `settings.FRONTEND_ORIGIN` instead of hardcoded `localhost:3000`
- Keep health check endpoint

---

### 7. Integration Tests

#### [NEW] tests/test_auth.py
Tests using `TestClient` against a **SQLite in-memory** test DB (override `get_db` via FastAPI's dependency overriding) to avoid needing a live Postgres during CI:

- `conftest.py` with: `engine` (SQLite), `tables` fixture (create all), `client` fixture, `authenticated_client(role=...)` fixture
- Test cases a-i as specified

> [!IMPORTANT]
> Tests use SQLite in-memory (not the Docker Postgres) to run without Docker. The `authenticated_client(role)` fixture is a pytest fixture factory that registers+logs-in a user of the given role and returns a `TestClient` with cookies attached. All future modules can import it from `tests/conftest.py`.

---

## Verification Plan

### Automated Tests
```bash
cd /home/aditya/Clinic_Booking_System/clinic-app/backend
.venv/bin/pytest tests/test_auth.py -v
```

All 9 test cases (a through i) must pass green.

### Key Design Decisions
1. **Auto-login on register**: cookies issued immediately on `POST /auth/register`
2. **Cookie-only tokens**: JWT never appears in response body
3. **SQLite for tests**: no Docker dependency for unit/integration tests
4. **`authenticated_client` in conftest**: reusable across all future modules
