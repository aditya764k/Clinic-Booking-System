# Graph Report - clinic-app  (2026-09-25)

## Corpus Check
- 32 files · ~18,105 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 323 nodes · 528 edges · 22 communities detected
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 130 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 22|Community 22]]

## God Nodes (most connected - your core abstractions)
1. `User` - 26 edges
2. `DoctorProfile` - 23 edges
3. `authenticated_client()` - 21 edges
4. `PatientProfile` - 19 edges
5. `Appointment` - 19 edges
6. `_register()` - 16 edges
7. `Base` - 15 edges
8. `AppointmentSlot` - 12 edges
9. `register()` - 11 edges
10. `TestRegister` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Vite Build Configuration` --conceptually_related_to--> `Clinic Booking System Overview`  [INFERRED]
  frontend/vite.config.ts → README.md
- `register()` --rationale_for--> `Register a new user and auto-login (issues cookies).      Creates the matching P`  [EXTRACTED]
  backend/app/api/auth.py → app/api/auth.py
- `login()` --rationale_for--> `Authenticate with email + password and issue HttpOnly cookies.`  [EXTRACTED]
  backend/app/api/auth.py → app/api/auth.py
- `refresh_access_token()` --rationale_for--> `Issue a new access token using the refresh token cookie.      The access token d`  [EXTRACTED]
  backend/app/api/auth.py → app/api/auth.py
- `logout()` --rationale_for--> `Clear both auth cookies, effectively logging the user out.      Does not require`  [EXTRACTED]
  backend/app/api/auth.py → app/api/auth.py

## Hyperedges (group relationships)
- **Authentication Architecture** — module_2_auth_rbac_summary_authentication, module_2_auth_rbac_summary_httponly_cookies, module_2_auth_rbac_summary_jwt, module_2_auth_rbac_summary_rbac [EXTRACTED 1.00]

## Communities (31 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (33): _doctor_only(), _has_httponly_cookie(), _login(), Module 2 — Authentication & RBAC Integration Tests =============================, Password under 8 chars → 422 validation error., Unknown role → 422 validation error., Second registration with same email → 409 Conflict., Successful login sets access_token + refresh_token as HttpOnly cookies. (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (24): authenticated_client(), Factory fixture that returns a TestClient with auth cookies set.      Usage in t, Doctor token accepted by require_role("doctor") → 200., Patient token rejected by require_role("doctor") → 403., Receptionist accepted by require_role("doctor", "receptionist") → 200., Patient rejected by require_role("doctor", "receptionist") → 403., TestRBAC, T1 — Doctor can set working-hours config. (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (30): Base, Base, DeclarativeBase, Appointment, AppointmentStatus, ClinicalNote, Appointment and ClinicalNote models, AuditLog (+22 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (29): _clear_auth_cookies(), google_callback(), google_login(), login(), logout(), Authentication endpoints.  All endpoints live under the /auth prefix (set in mai, Register a new user and auto-login (issues cookies).      Creates the matching P, Register a new user and auto-login (issues cookies).      Creates the matching P (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (18): BaseModel, full_name_not_empty(), LoginRequest, password_min_length(), Pydantic schemas for the authentication module.  Rules: - ``hashed_password`` is, RegisterRequest, UserOut, AppointmentOut (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (17): create_access_token(), create_refresh_token(), decode_token(), hash_password(), InvalidTokenError, Security utilities: password hashing and JWT operations.  All JWT operations go, Return bcrypt hash of *plain* password., Constant-time compare of *plain* against stored *hashed* password.      Uses pas (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (11): make_role_client(), Integration tests for Module 3: Scheduling & Availability.  Test IDs -------- T1, Register a doctor, set config, return the client., Get the doctor profile id via whoami., T3 — Generating slots for a Monday creates ASSERT_SLOT_COUNT slots., T4 — Calling generate twice produces no duplicates., T11 — A doctor calling generate for a different doctor_id gets 403., T12 — A receptionist can generate slots for any doctor. (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (14): book_appointment(), generate_slots(), list_open_slots(), Scheduling & Availability API endpoints.  Endpoints --------- PATCH  /doctors/me, List open (unbooked) appointment slots for a doctor on a given date.      Return, Book an open appointment slot for the currently authenticated patient.      # TO, Set or update the calling doctor's working-hours configuration.      Stores the, Generate appointment slots for a doctor on a given date.      - A ``doctor`` cal (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.29
Nodes (8): client(), db_session(), Pytest configuration and shared fixtures for the Clinic Booking System test suit, Create all tables before each test, drop after., Yield a database session for direct DB inspection in tests., TestClient with the get_db dependency overridden to use SQLite., set_sqlite_pragma(), setup_database()

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (5): make_patient_client(), Return the active get_db override (set by the ``client`` fixture)., T9 — Run 5× concurrency races; each must yield exactly 1×201 + 1×409., T10 — After the race, the winning slot is absent from GET /slots., Create an independent TestClient (own cookie jar) for a unique patient.

### Community 10 - "Community 10"
Cohesion: 0.38
Nodes (5): get_current_user(), FastAPI dependency functions for authentication and role-based access control., Extract and validate the access token from the ``access_token`` cookie.      Ret, Dependency factory for role-based access control.      Usage examples::, require_role()

### Community 11 - "Community 11"
Cohesion: 0.33
Nodes (5): Alembic env.py -- wired to our SQLAlchemy Base and DATABASE_URL from .env, Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 12 - "Community 12"
Cohesion: 0.5
Nodes (3): BaseSettings, Application configuration via pydantic-settings.  All secrets are read from envi, Settings

### Community 13 - "Community 13"
Cohesion: 0.4
Nodes (5): Initial Empty Alembic Migration, Environment Configuration, Environment Variables Template, Setup Instructions, Backend Python Dependencies

### Community 14 - "Community 14"
Cohesion: 0.4
Nodes (5): Clinic Booking Data Model, Authentication Module, HttpOnly Cookies, JSON Web Tokens, Role-Based Access Control

### Community 16 - "Community 16"
Cohesion: 0.5
Nodes (3): get_db(), Database engine, session factory, and declarative Base. All models import Base f, FastAPI dependency – yields a DB session and closes it after the request.

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (3): Global CSS Styles, Clinic Booking System Overview, Vite Build Configuration

## Knowledge Gaps
- **123 isolated node(s):** `Attach access + refresh token cookies to *response*.`, `Expire both auth cookies (effectively logging the user out).`, `Return the role as a plain string regardless of whether it's an Enum or str.`, `Register a new user and auto-login (issues cookies).      Creates the matching P`, `Authenticate with email + password and issue HttpOnly cookies.` (+118 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **Why does `DoctorProfile` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Why does `register()` connect `Community 3` to `Community 2`, `Community 5`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `User` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`User` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `DoctorProfile` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`DoctorProfile` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `authenticated_client()` (e.g. with `.test_doctor_role_accepted_on_doctor_endpoint()` and `.test_patient_role_rejected_on_doctor_endpoint()`) actually correct?**
  _`authenticated_client()` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `PatientProfile` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`PatientProfile` has 17 INFERRED edges - model-reasoned connections that need verification._