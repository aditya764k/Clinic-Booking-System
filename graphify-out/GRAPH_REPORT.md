# Graph Report - clinic-app  (2026-09-24)

## Corpus Check
- 19 files · ~5,157 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 72 nodes · 116 edges · 13 communities detected
- Extraction: 52% EXTRACTED · 48% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.55)
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
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 14|Community 14]]

## God Nodes (most connected - your core abstractions)
1. `Base` - 15 edges
2. `Appointment` - 13 edges
3. `User` - 12 edges
4. `AppointmentSlot` - 11 edges
5. `PatientProfile` - 10 edges
6. `DoctorProfile` - 10 edges
7. `Invoice` - 10 edges
8. `ClinicalNote` - 9 edges
9. `UserRole` - 8 edges
10. `main()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Clinic Booking System Overview` --conceptually_related_to--> `Vite Build Configuration`  [INFERRED]
  README.md → frontend/vite.config.ts
- `Vite Build Configuration` --conceptually_related_to--> `Global CSS Styles`  [INFERRED]
  frontend/vite.config.ts → frontend/src/index.css
- `Initial Empty Alembic Migration` --conceptually_related_to--> `Backend Python Dependencies`  [INFERRED]
  backend/alembic/versions/287c78c5959f_initial_empty_migration.py → backend/requirements.txt
- `InvoiceStatus` --uses--> `User`  [INFERRED]
  backend/app/models/billing.py → backend/app/models/identity.py
- `PaymentMethod` --uses--> `User`  [INFERRED]
  backend/app/models/billing.py → backend/app/models/identity.py

## Hyperedges (group relationships)
- **Frontend Setup and Branding Assets** — vite_config_vite_configuration, index_global_styles, vite_logo, react_logo [INFERRED 0.85]
- **Backend Configuration and Database Setup** — env_config, requirements_backend_dependencies, 287c78c5959f_initial_empty_migration_initial_migration [INFERRED 0.85]
- **Project Documentation and Environment Templates** — readme_clinic_booking_system, readme_setup_instructions, env_example_template [INFERRED 0.85]

## Communities (20 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.39
Nodes (16): Base, Base, DeclarativeBase, Appointment, AppointmentStatus, ClinicalNote, Appointment and ClinicalNote models, AuditLog (+8 more)

### Community 1 - "Community 1"
Cohesion: 0.33
Nodes (5): Alembic env.py -- wired to our SQLAlchemy Base and DATABASE_URL from .env, Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 2 - "Community 2"
Cohesion: 0.47
Nodes (5): cleanup(), hr(), main(), scripts/verify_module1.py ========================= Module 1 verification script, Remove any rows from a prior run so the script is idempotent.

### Community 3 - "Community 3"
Cohesion: 0.5
Nodes (4): InvoiceStatus, PaymentMethod, Billing models: Invoice, WebhookEvent, str

### Community 4 - "Community 4"
Cohesion: 0.4
Nodes (5): Initial Empty Alembic Migration, Environment Configuration, Environment Variables Template, Setup Instructions, Backend Python Dependencies

### Community 5 - "Community 5"
Cohesion: 0.5
Nodes (3): get_db(), Database engine, session factory, and declarative Base. All models import Base f, FastAPI dependency – yields a DB session and closes it after the request.

### Community 8 - "Community 8"
Cohesion: 0.67
Nodes (3): Global CSS Styles, Clinic Booking System Overview, Vite Build Configuration

## Knowledge Gaps
- **21 isolated node(s):** `Identity models: User, PatientProfile, DoctorProfile`, `Scheduling models: AppointmentSlot`, `Appointment and ClinicalNote models`, `Billing models: Invoice, WebhookEvent`, `Audit models: AuditLog` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Base` connect `Community 0` to `Community 3`, `Community 5`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `AppointmentSlot` connect `Community 0` to `Community 10`, `Community 2`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Base` (e.g. with `UserRole` and `User`) actually correct?**
  _`Base` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Appointment` (e.g. with `UserRole` and `User`) actually correct?**
  _`Appointment` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `User` (e.g. with `Base` and `AuditLog`) actually correct?**
  _`User` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `AppointmentSlot` (e.g. with `UserRole` and `User`) actually correct?**
  _`AppointmentSlot` has 9 INFERRED edges - model-reasoned connections that need verification._