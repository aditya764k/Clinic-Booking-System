# Graph Report - clinic-app  (2026-09-25)

## Corpus Check
- 36 files · ~21,084 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 397 nodes · 727 edges · 22 communities detected
- Extraction: 73% EXTRACTED · 27% INFERRED · 0% AMBIGUOUS · INFERRED: 196 edges (avg confidence: 0.6)
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
1. `User` - 34 edges
2. `DoctorProfile` - 31 edges
3. `PatientProfile` - 26 edges
4. `Appointment` - 26 edges
5. `register_user()` - 23 edges
6. `authenticated_client()` - 21 edges
7. `_seed()` - 20 edges
8. `AppointmentSlot` - 19 edges
9. `TestRBAC` - 19 edges
10. `_register()` - 16 edges

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

## Communities (31 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (34): _doctor_only(), _has_httponly_cookie(), _login(), Module 2 — Authentication & RBAC Integration Tests =============================, Password under 8 chars → 422 validation error., Unknown role → 422 validation error., Second registration with same email → 409 Conflict., Successful login sets access_token + refresh_token as HttpOnly cookies. (+26 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (26): authenticated_client(), Factory fixture that returns a TestClient with auth cookies set.      Usage in t, Doctor token accepted by require_role("doctor") → 200., Patient token rejected by require_role("doctor") → 403., Receptionist accepted by require_role("doctor", "receptionist") → 200., Patient rejected by require_role("doctor", "receptionist") → 403., make_patient_client(), T1 — Doctor can set working-hours config. (+18 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (17): IllegalTransitionError, Domain exceptions for the Clinic Appointment Manager.  Rules: - IllegalTransitio, Raised when a caller attempts an invalid appointment status transition.      Thi, hash_password(), Return bcrypt hash of *plain* password., login(), Integration tests for Module 4: Appointment State Machine., Register a user; return profile_id (None for receptionist — no profile table). (+9 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (37): Base, Base, DeclarativeBase, Appointment, AppointmentStatus, ClinicalNote, Appointment and ClinicalNote models, AuditLog (+29 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (29): _clear_auth_cookies(), google_callback(), google_login(), login(), logout(), Authentication endpoints.  All endpoints live under the /auth prefix (set in mai, Register a new user and auto-login (issues cookies).      Creates the matching P, Register a new user and auto-login (issues cookies).      Creates the matching P (+21 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (20): BaseModel, full_name_not_empty(), LoginRequest, password_min_length(), Pydantic schemas for the authentication module.  Rules: - ``hashed_password`` is, RegisterRequest, UserOut, AppointmentOut (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (20): get_current_user(), FastAPI dependency functions for authentication and role-based access control., Extract and validate the access token from the ``access_token`` cookie.      Ret, Dependency factory for role-based access control.      Usage examples::, require_role(), create_access_token(), create_refresh_token(), decode_token() (+12 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (21): _appointment_out(), cancel(), check_in(), doctor_queue_mine(), _queue_item(), Appointment State Machine API endpoints.  Endpoints --------- POST  /appointment, FR-REC-01: All appointments for today, sorted by lifecycle order.      Returns a, FR-DOC-01: Doctor's own appointments for today (or a specific date).      The do (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (14): book_appointment(), generate_slots(), list_open_slots(), Scheduling & Availability API endpoints.  Endpoints --------- PATCH  /doctors/me, List open (unbooked) appointment slots for a doctor on a given date.      Return, Book an open appointment slot for the currently authenticated patient.      # TO, Set or update the calling doctor's working-hours configuration.      Stores the, Generate appointment slots for a doctor on a given date.      - A ``doctor`` cal (+6 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (8): make_role_client(), Register a doctor, set config, return the client., T3 — Generating slots for a Monday creates ASSERT_SLOT_COUNT slots., T4 — Calling generate twice produces no duplicates., T11 — A doctor calling generate for a different doctor_id gets 403., T12 — A receptionist can generate slots for any doctor., T3b — Sunday is null in config, so generate returns []., Create an independent TestClient (own cookie jar) for a specific role.

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (8): client(), db_session(), Pytest configuration and shared fixtures for the Clinic Booking System test suit, Create all tables before each test, drop after., Yield a database session for direct DB inspection in tests., TestClient with the get_db dependency overridden to use SQLite., set_sqlite_pragma(), setup_database()

### Community 11 - "Community 11"
Cohesion: 0.33
Nodes (5): Alembic env.py -- wired to our SQLAlchemy Base and DATABASE_URL from .env, Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 12 - "Community 12"
Cohesion: 0.4
Nodes (4): health_check(), illegal_transition_handler(), FastAPI application entry point.  CORS is configured with allow_credentials=True, Convert IllegalTransitionError → HTTP 409 with structured JSON body.

### Community 13 - "Community 13"
Cohesion: 0.5
Nodes (3): BaseSettings, Application configuration via pydantic-settings.  All secrets are read from envi, Settings

### Community 14 - "Community 14"
Cohesion: 0.4
Nodes (5): Initial Empty Alembic Migration, Environment Configuration, Environment Variables Template, Setup Instructions, Backend Python Dependencies

### Community 15 - "Community 15"
Cohesion: 0.4
Nodes (5): Clinic Booking Data Model, Authentication Module, HttpOnly Cookies, JSON Web Tokens, Role-Based Access Control

### Community 16 - "Community 16"
Cohesion: 0.5
Nodes (3): get_db(), Database engine, session factory, and declarative Base. All models import Base f, FastAPI dependency – yields a DB session and closes it after the request.

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (3): Global CSS Styles, Clinic Booking System Overview, Vite Build Configuration

## Knowledge Gaps
- **141 isolated node(s):** `Convert IllegalTransitionError → HTTP 409 with structured JSON body.`, `Attach access + refresh token cookies to *response*.`, `Expire both auth cookies (effectively logging the user out).`, `Return the role as a plain string regardless of whether it's an Enum or str.`, `Register a new user and auto-login (issues cookies).      Creates the matching P` (+136 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`?**
  _High betweenness centrality (0.186) - this node is a cross-community bridge._
- **Why does `DoctorProfile` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Why does `Appointment` connect `Community 3` to `Community 8`, `Community 1`, `Community 2`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `User` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`User` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `DoctorProfile` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`DoctorProfile` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `PatientProfile` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`PatientProfile` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `Appointment` (e.g. with `UserRole` and `User`) actually correct?**
  _`Appointment` has 24 INFERRED edges - model-reasoned connections that need verification._