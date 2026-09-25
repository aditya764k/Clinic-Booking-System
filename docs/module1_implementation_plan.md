# Module 1: Core Database Layer (Implementation Plan)

## Goal Description
Implement the foundational database layer for the Clinic Appointment Management system. This involves defining SQLAlchemy 2.0 ORM models for identity, scheduling, appointments, billing, and audit logs. The database backend will be PostgreSQL, requiring the use of native PostgreSQL Enums and timezone-aware timestamps for precise scheduling and auditing. We will also configure automated Alembic migrations to enforce schema constraints.

## Proposed Changes

### Database Configuration
- Configure the SQLAlchemy engine to connect to PostgreSQL via `DATABASE_URL`.
- Implement a session dependency for FastAPI using `sessionmaker`.
- Ensure timezone-aware datetime types (`DateTime(timezone=True)`) are used across all tables.

### Data Models

#### [NEW] `backend/app/models/identity.py`
- **User**: Core authentication table (`id`, `email`, `hashed_password`, `role`).
- **PatientProfile**: Linked to `User` via one-to-one relationship. Contains patient-specific info (`full_name`, `date_of_birth`, `phone`).
- **DoctorProfile**: Linked to `User` via one-to-one relationship. Contains doctor-specific info (`full_name`, `specialty`, `bio`).

#### [NEW] `backend/app/models/scheduling.py`
- **AppointmentSlot**: Represents a doctor's availability. 
- Fields: `id`, `doctor_id`, `start_time`, `end_time`, `is_booked`.
- Constraints: Add a `UniqueConstraint` on `(doctor_id, start_time)` to prevent overlapping or duplicate slots for the same doctor.

#### [NEW] `backend/app/models/appointment.py`
- **Appointment**: Represents a booked appointment.
- Fields: `id`, `patient_id`, `doctor_id`, `slot_id`, `status` (PostgreSQL ENUM: `SCHEDULED`, `COMPLETED`, `CANCELLED`), `notes`.
- **ClinicalNote**: Represents private doctor notes linked to an appointment.
- Fields: `id`, `appointment_id`, `doctor_id`, `content`.

#### [NEW] `backend/app/models/billing.py`
- **Invoice**: Financial record for completed appointments.
- Fields: `id`, `patient_id`, `appointment_id`, `amount_due`, `status` (ENUM: `DRAFT`, `PAID`, `VOID`).
- **WebhookEvent**: Audit trail for payment gateway webhooks (e.g., Razorpay/Stripe).
- Fields: `id`, `event_type`, `payload`, `processed_at`.

#### [NEW] `backend/app/models/audit.py`
- **AuditLog**: Generic logging table for critical system events.
- Fields: `id`, `user_id`, `action`, `resource`, `timestamp`.

### Migrations
- Initialize Alembic using `alembic init alembic`.
- Configure `alembic/env.py` to import all models from `app.models.*` so they are automatically detected.
- Generate the initial migration script: `alembic revision --autogenerate -m "Initial schema"`.

## Verification Plan

### Automated Tests
- Write a verification script (`verify_module1.py`) that interacts with the database to:
  1. Create a Doctor and a Patient.
  2. Create an AppointmentSlot.
  3. Attempt to create a duplicate slot (expecting an IntegrityError).
  4. Book an Appointment.
  5. Generate an Invoice.
- Run the script in a Docker container connected to a real PostgreSQL instance to ensure PostgreSQL-specific constraints (Enums, Timezones, Unique constraints) function correctly.
