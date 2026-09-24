# Module 3: Scheduling & Availability Summary

## Overview
Module 3 is responsible for handling the core business logic of the Clinic Appointment Manager: doctors generating their availability, patients viewing open slots, and patients securely booking those slots. The primary technical challenge of this module is handling high concurrency (race conditions where multiple patients attempt to book the exact same slot at the exact same millisecond) without overcomplicating the system with explicit locks.

---

## 1. Core Concepts & Approaches

### A. Pre-Generated Slots vs. On-The-Fly Generation
**Approach:** Availability is **pre-generated** into physical database rows (`appointment_slots`) rather than being computed on-the-fly during a booking request. 
**Why:**
- It allows receptionists to generate a doctor's schedule months in advance.
- It makes the `GET /slots` query incredibly fast (a simple `LEFT JOIN` against `appointments`).
- Most importantly, it gives the booking system a physical row to anchor to, allowing us to use strict foreign keys and unique database constraints for concurrency control.

### B. Idempotency in Slot Generation
**Approach:** The `POST /doctors/{id}/slots/generate` endpoint is designed to be **idempotent**. You can call it 100 times for the same date, and it will only ever create the slots once, silently skipping any duplicates.
**How it works:**
- We rely on a composite `UNIQUE` constraint on the `appointment_slots` table: `(doctor_id, slot_start)`.
- When generating slots, we use SQLAlchemy's `begin_nested()` (savepoints). We attempt to `INSERT` each generated slot. If it throws an `IntegrityError` (because the slot already exists), we roll back *just that savepoint* and continue to the next one.
- **Portability:** This acts exactly like PostgreSQL's `INSERT ... ON CONFLICT DO NOTHING`, but is entirely portable and works seamlessly with SQLite for local development.

### C. Lock-Free Concurrency for Booking
**Approach:** The `POST /appointments/book` endpoint completely avoids "check-then-act" application-level logic (e.g., querying if the slot is open, and if so, booking it).
**Why:** Check-then-act causes race conditions under heavy load because the slot might be taken in the few milliseconds between the `SELECT` and the `INSERT`. 
**How it works:**
- We skip the `SELECT` check entirely and attempt to `INSERT` the `Appointment` row directly.
- The `appointments` table has a strict `UNIQUE` constraint on `slot_id`.
- If two users try to book simultaneously, the database engine (which natively handles atomic writes) will allow exactly one `INSERT` to succeed. The loser will trigger an `IntegrityError` from the database.
- We catch this `IntegrityError` (and SQLAlchemy's `InvalidRequestError` for SQLite thread-sharing artifacts), roll back the transaction, and return a clean `409 Conflict` HTTP response to the user.

---

## 2. API Endpoints

| Method | Endpoint | Role Required | Description |
|--------|----------|---------------|-------------|
| `PATCH` | `/doctors/me/working-hours` | `doctor` | Allows a doctor to define their weekly JSON schedule config (e.g., 9-5 on Mondays, 30 min slots). |
| `POST` | `/doctors/{doctor_id}/slots/generate` | `doctor`, `receptionist` | Uses the config to idempotently generate physical slot rows for a specific date. |
| `GET` | `/slots` | `Any Authenticated User` | Returns a list of *available* slots for a doctor on a given date. |
| `POST` | `/appointments/book` | `patient` | Books a slot. Fails with `409` if the slot was just taken. |

---

## 3. Implementation Details & Logic

### Availability Filtering (The LEFT JOIN pattern)
To find slots that are *open*, we don't store a `status` boolean on the slot itself. Instead, a slot is considered open if it has **no linked appointment**.
The SQLAlchemy query uses a `LEFT OUTER JOIN` from `AppointmentSlot` to `Appointment`. By filtering for `Appointment.id.is_(None)`, we instantly get only the slots that haven't been booked.

### Identifying Users vs. Profiles
In Module 2, we separated Identity (`users`) from Data (`patient_profiles`, `doctor_profiles`). 
In Module 3, it is critical to remember that endpoints like slot generation require the **Doctor Profile ID**, not the User ID. 
- *Improvement made:* We updated the `/auth/whoami` endpoint (and the `UserOut` schema) to dynamically calculate and return the `profile_id`. This prevents the frontend from confusing the base `user.id` (used for login) with the `profile_id` (used for business logic).

---

## 4. Important Points & Things to Remember

1. **Do not use `time.sleep()` or `SELECT` checks for concurrency.** Trust the database constraints. The `UNIQUE(slot_id)` constraint on the `appointments` table is the absolute source of truth.
2. **SQLite StaticPool Quirks:** When testing concurrency in `pytest`, SQLite's `StaticPool` shares one connection across multiple test threads. If Thread A rolls back, it can reset the database cursor for Thread B, resulting in an `InvalidRequestError` (formerly `FlushError`) in Thread B. We catch this explicitly in the `book_appointment` endpoint to ensure tests pass cleanly without crashing the API.
3. **Database Consistency:** Because booking creates an `Appointment` row linking to an `AppointmentSlot`, and the slot links to `DoctorProfile`, attempting to delete a doctor would cascade properly. However, for audit reasons, soft-deletes are generally preferred over hard deletes in production clinical systems.
4. **Timezones:** All datetimes in the slots are created and stored using UTC (`timezone.utc`). The frontend is responsible for converting these UTC slots into the patient's local timezone.

---

## 5. Testing Strategy
- **Unit Tests:** Validated that `GET /slots` correctly filters out booked slots, and that generating slots on a Sunday (if configured to be off) returns `[]`.
- **RBAC Tests:** Verified that patients get a `403 Forbidden` if they try to configure a doctor's hours, and doctors get a `403` if they try to book an appointment (patients only).
- **Concurrency Integration Tests:** We utilized Python's `threading` module to create two independent `TestClient` sessions representing two distinct patients. We fired simultaneous requests to `/appointments/book` for the exact same slot ID and strictly asserted that:
  1. Only one 201 response is allowed (or one fails with 409).
  2. The database contains exactly `1` appointment row for that slot.
