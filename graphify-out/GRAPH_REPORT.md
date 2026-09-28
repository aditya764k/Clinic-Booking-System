# Graph Report - clinic-app  (2026-09-29)

## Corpus Check
- 61 files · ~36,154 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 593 nodes · 1102 edges · 24 communities detected
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 280 edges (avg confidence: 0.61)
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
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 32|Community 32]]

## God Nodes (most connected - your core abstractions)
1. `Appointment` - 37 edges
2. `User` - 36 edges
3. `DoctorProfile` - 33 edges
4. `AppointmentSlot` - 30 edges
5. `PatientProfile` - 28 edges
6. `AppointmentStatus` - 23 edges
7. `authenticated_client()` - 23 edges
8. `register_user()` - 23 edges
9. `_seed_appointment()` - 23 edges
10. `register_user()` - 21 edges

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

## Communities (45 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (36): authenticated_client(), Factory fixture that returns a TestClient with auth cookies set.      Usage in t, Factory fixture that returns a TestClient with auth cookies set.      Usage in t, Factory fixture that returns a TestClient with auth cookies set.      Usage in t, Doctor token accepted by require_role("doctor") → 200., Patient token rejected by require_role("doctor") → 403., Receptionist accepted by require_role("doctor", "receptionist") → 200., Patient rejected by require_role("doctor", "receptionist") → 403. (+28 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (49): Register a new user and auto-login (issues cookies).      Creates the matching P, Register a new user and auto-login (issues cookies).      Creates the matching P, register(), Base, Base, hash_password(), Return bcrypt hash of *plain* password., DeclarativeBase (+41 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (34): _doctor_only(), _has_httponly_cookie(), _login(), Module 2 — Authentication & RBAC Integration Tests =============================, Password under 8 chars → 422 validation error., Unknown role → 422 validation error., Second registration with same email → 409 Conflict., Successful login sets access_token + refresh_token as HttpOnly cookies. (+26 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (43): create_invoice(), create_razorpay_order(), _get_invoice_or_404(), _invoice_out(), pay_cash(), Billing & Payments API endpoints — Module 6.  Endpoints --------- POST /appointm, FR-REC-04: Receptionist creates an invoice for a completed appointment.      Gua, FR-BILL-01: Create a Razorpay order for an invoice.      Mutual exclusivity guar (+35 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (43): _appointment_out(), cancel(), check_in(), doctor_queue_mine(), _queue_item(), Appointment State Machine API endpoints.  Endpoints --------- POST  /appointment, FR-REC-01: All appointments for today, sorted by lifecycle order.      Returns a, FR-DOC-01: Doctor's own appointments for today (or a specific date).      The do (+35 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (24): AIDraftGenerationError, Raised by generate_clinical_draft() when the Gemini call fails.      The FastAPI, AppointmentStatus, AIDraftOut, The structured draft returned by the Gemini service.      Matches the JSON shape, login(), Integration tests for Module 5: Doctor Console & AI-Assisted Clinical Notes.  Te, Calling /draft twice must update the same row, not create two rows. (+16 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (41): _clear_auth_cookies(), google_callback(), google_login(), login(), logout(), Authentication endpoints.  All endpoints live under the /auth prefix (set in mai, Authenticate with email + password and issue HttpOnly cookies., Authenticate with email + password and issue HttpOnly cookies. (+33 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (12): IllegalTransitionError, Domain exceptions for the Clinic Appointment Manager.  Rules: - IllegalTransitio, Raised when a caller attempts an invalid appointment status transition.      Thi, Raised when a caller attempts an invalid appointment status transition.      Thi, login(), Register a user; return profile_id (None for receptionist — no profile table)., Log in as an already-registered user (rotates the shared cookie jar)., register_user() (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (37): _make_signature(), Module 6 test suite: Billing & Payments (Razorpay + Cash).  Tests are grouped in, Receptionist can create an invoice for a completed appointment., Creating an invoice twice returns the same invoice — no duplicate., Razorpay order endpoint returns order_id and sets payment_method., Helper: creates invoice and a Razorpay order. Returns (invoice_id, order_id)., Valid webhook atomically marks Invoice and Appointment as PAID., Webhook with bad signature is rejected 400, state unchanged. (+29 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (14): book_appointment(), generate_slots(), list_open_slots(), Scheduling & Availability API endpoints.  Endpoints --------- PATCH  /doctors/me, List open (unbooked) appointment slots for a doctor on a given date.      Return, Book an open appointment slot for the currently authenticated patient.      # TO, Set or update the calling doctor's working-hours configuration.      Stores the, Generate appointment slots for a doctor on a given date.      - A ``doctor`` cal (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.16
Nodes (14): client(), db_session(), Pytest configuration and shared fixtures for the Clinic Booking System test suit, Create all tables before each test, drop after., Create all tables before each test, drop after., Create all tables before each test, drop after., Yield a database session for direct DB inspection in tests., Yield a database session for direct DB inspection in tests. (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.2
Nodes (9): ai_draft_error_handler(), health_check(), illegal_transition_handler(), FastAPI application entry point.  CORS is configured with allow_credentials=True, Convert IllegalTransitionError → HTTP 409 with structured JSON body., Convert IllegalTransitionError → HTTP 409 with structured JSON body., Convert IllegalTransitionError → HTTP 409 with structured JSON body., Convert AIDraftGenerationError → HTTP 502 with structured JSON body. (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.38
Nodes (5): get_current_user(), FastAPI dependency functions for authentication and role-based access control., Extract and validate the access token from the ``access_token`` cookie.      Ret, Dependency factory for role-based access control.      Usage examples::, require_role()

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (5): Alembic env.py -- wired to our SQLAlchemy Base and DATABASE_URL from .env, Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 15 - "Community 15"
Cohesion: 0.5
Nodes (3): BaseSettings, Application configuration via pydantic-settings.  All secrets are read from envi, Settings

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (5): Initial Empty Alembic Migration, Environment Configuration, Environment Variables Template, Setup Instructions, Backend Python Dependencies

### Community 17 - "Community 17"
Cohesion: 0.4
Nodes (5): Clinic Booking Data Model, Authentication Module, HttpOnly Cookies, JSON Web Tokens, Role-Based Access Control

### Community 18 - "Community 18"
Cohesion: 0.5
Nodes (3): get_db(), Database engine, session factory, and declarative Base. All models import Base f, FastAPI dependency – yields a DB session and closes it after the request.

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (3): Global CSS Styles, Clinic Booking System Overview, Vite Build Configuration

## Knowledge Gaps
- **208 isolated node(s):** `Convert IllegalTransitionError → HTTP 409 with structured JSON body.`, `Convert AIDraftGenerationError → HTTP 502 with structured JSON body.`, `Attach access + refresh token cookies to *response*.`, `Expire both auth cookies (effectively logging the user out).`, `Return the role as a plain string regardless of whether it's an Enum or str.` (+203 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Appointment` connect `Community 1` to `Community 0`, `Community 10`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `User` connect `Community 1` to `Community 0`, `Community 2`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Why does `DoctorProfile` connect `Community 1` to `Community 0`, `Community 2`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Appointment` (e.g. with `UserRole` and `User`) actually correct?**
  _`Appointment` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `User` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`User` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `DoctorProfile` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`DoctorProfile` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `AppointmentSlot` (e.g. with `UserRole` and `User`) actually correct?**
  _`AppointmentSlot` has 28 INFERRED edges - model-reasoned connections that need verification._