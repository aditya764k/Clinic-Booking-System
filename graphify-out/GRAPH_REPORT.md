# Graph Report - .  (2026-09-25)

## Corpus Check
- 0 files · ~0 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 213 nodes · 297 edges · 19 communities detected
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.6)
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
- [[_COMMUNITY_Community 19|Community 19]]

## God Nodes (most connected - your core abstractions)
1. `Base` - 15 edges
2. `_register()` - 15 edges
3. `Appointment` - 13 edges
4. `User` - 12 edges
5. `AppointmentSlot` - 11 edges
6. `PatientProfile` - 10 edges
7. `DoctorProfile` - 10 edges
8. `Invoice` - 10 edges
9. `ClinicalNote` - 9 edges
10. `UserRole` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Vite Build Configuration` --conceptually_related_to--> `Clinic Booking System Overview`  [INFERRED]
  frontend/vite.config.ts → README.md
- `Global CSS Styles` --conceptually_related_to--> `Vite Build Configuration`  [INFERRED]
  frontend/src/index.css → frontend/vite.config.ts
- `Initial Empty Alembic Migration` --conceptually_related_to--> `Backend Python Dependencies`  [INFERRED]
  backend/alembic/versions/287c78c5959f_initial_empty_migration.py → backend/requirements.txt
- `Environment Variables Template` --references--> `Environment Configuration`  [EXTRACTED]
  .env.example → .env
- `Environment Variables Template` --references--> `Setup Instructions`  [EXTRACTED]
  .env.example → README.md

## Hyperedges (group relationships)
- **Authentication Architecture** — module_2_auth_rbac_summary_authentication, module_2_auth_rbac_summary_httponly_cookies, module_2_auth_rbac_summary_jwt, module_2_auth_rbac_summary_rbac [EXTRACTED 1.00]

## Communities (26 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (36): _clear_auth_cookies(), google_callback(), google_login(), login(), logout(), Authentication endpoints.  All endpoints live under the /auth prefix (set in mai, Register a new user and auto-login (issues cookies).      Creates the matching P, Authenticate with email + password and issue HttpOnly cookies. (+28 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (22): _has_httponly_cookie(), _login(), Module 2 — Authentication & RBAC Integration Tests =============================, Password under 8 chars → 422 validation error., Unknown role → 422 validation error., Second registration with same email → 409 Conflict., Successful login sets access_token + refresh_token as HttpOnly cookies., Login response body is UserOut (no password field). (+14 more)

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (27): Base, Base, DeclarativeBase, Appointment, AppointmentStatus, ClinicalNote, Appointment and ClinicalNote models, AuditLog (+19 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (14): authenticated_client(), client(), db_session(), Pytest configuration and shared fixtures for the Clinic Booking System test suit, Create all tables before each test, drop after., Yield a database session for direct DB inspection in tests., TestClient with the get_db dependency overridden to use SQLite., Factory fixture that returns a TestClient with auth cookies set.      Usage in t (+6 more)

### Community 4 - "Community 4"
Cohesion: 0.22
Nodes (8): Return the identity of the currently authenticated user.      Identity is derive, _user_out(), whoami(), BaseModel, LoginRequest, Pydantic schemas for the authentication module.  Rules: - ``hashed_password`` is, RegisterRequest, UserOut

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (6): GET /auth/whoami with no cookie → 401., GET /auth/whoami with valid cookie → 200 and correct identity., GET /auth/whoami with a forged token → 401., GET /auth/whoami with a legitimately expired token → 401., Using a refresh token where an access token is expected → 401., TestWhoami

### Community 6 - "Community 6"
Cohesion: 0.33
Nodes (5): Alembic env.py -- wired to our SQLAlchemy Base and DATABASE_URL from .env, Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 7 - "Community 7"
Cohesion: 0.33
Nodes (5): get_current_user(), FastAPI dependency functions for authentication and role-based access control., Extract and validate the access token from the ``access_token`` cookie.      Ret, Dependency factory for role-based access control.      Usage examples::, require_role()

### Community 8 - "Community 8"
Cohesion: 0.4
Nodes (5): Initial Empty Alembic Migration, Environment Configuration, Environment Variables Template, Setup Instructions, Backend Python Dependencies

### Community 9 - "Community 9"
Cohesion: 0.4
Nodes (3): POST /auth/refresh with valid refresh cookie → 204, new access_token cookie., POST /auth/refresh with no refresh cookie → 401., TestRefresh

### Community 10 - "Community 10"
Cohesion: 0.4
Nodes (5): Clinic Booking Data Model, Authentication Module, HttpOnly Cookies, JSON Web Tokens, Role-Based Access Control

### Community 12 - "Community 12"
Cohesion: 0.5
Nodes (3): get_db(), Database engine, session factory, and declarative Base. All models import Base f, FastAPI dependency – yields a DB session and closes it after the request.

### Community 15 - "Community 15"
Cohesion: 0.5
Nodes (3): BaseSettings, Application configuration via pydantic-settings.  All secrets are read from envi, Settings

### Community 16 - "Community 16"
Cohesion: 0.67
Nodes (3): Global CSS Styles, Clinic Booking System Overview, Vite Build Configuration

## Knowledge Gaps
- **81 isolated node(s):** `Identity models: User, PatientProfile, DoctorProfile`, `Scheduling models: AppointmentSlot`, `Appointment and ClinicalNote models`, `Billing models: Invoice, WebhookEvent`, `Audit models: AuditLog` (+76 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `decode_token()` connect `Community 0` to `Community 9`, `Community 7`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Why does `_register()` connect `Community 1` to `Community 9`, `Community 5`?**
  _High betweenness centrality (0.171) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Base` (e.g. with `UserRole` and `User`) actually correct?**
  _`Base` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Appointment` (e.g. with `UserRole` and `User`) actually correct?**
  _`Appointment` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `User` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`User` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `AppointmentSlot` (e.g. with `UserRole` and `User`) actually correct?**
  _`AppointmentSlot` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Identity models: User, PatientProfile, DoctorProfile`, `Scheduling models: AppointmentSlot`, `Appointment and ClinicalNote models` to the rest of the system?**
  _81 weakly-connected nodes found - possible documentation gaps or missing edges._