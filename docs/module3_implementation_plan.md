# Module 3: Scheduling & Availability Implementation Plan

## Overview
Extend the Clinic Appointment Manager backend with:
- Doctor availability configuration (`working_hours_config` on `DoctorProfile`)
- Idempotent slot generation service
- Open-slot availability endpoint
- Concurrency-safe patient booking endpoint
- A full integration test suite, including a real threading-based concurrency test

---

## Key Design Decisions

> [!IMPORTANT]
> **Concurrency guarantee lives in the DB, not the app layer.** `appointments.slot_id` already has a `unique=True` constraint (Module 1). The booking endpoint does NOT do a pre-check SELECT + INSERT — that pattern has a TOCTOU race. Instead it attempts the INSERT directly and converts the `IntegrityError` on the `slot_id` unique constraint into a `409`. The UniqueConstraint IS the lock.

> [!NOTE]
> **SQLite caveat for tests.** SQLite does not have `INSERT ... ON CONFLICT DO NOTHING` with named constraints. The slot generation service will use `try/except IntegrityError` per-row (auto-rolls back the failed savepoint) which works identically on both SQLite and PostgreSQL. The concurrency test will use `threading` (two threads, two TestClient instances sharing one StaticPool engine) — SQLite's write serialization means one thread wins and the other gets the IntegrityError, identical to Postgres behaviour.

---

## Proposed Changes

### Schemas

#### [NEW] `backend/app/schemas/scheduling.py`
- **`DaySchedule`** — `start: str` (HH:MM), `end: str` (HH:MM), both validated as valid time strings.
- **`WorkingHoursConfig`** — `slot_duration_minutes: int` (5–240), `schedule: dict[str, DaySchedule | None]` where keys must be day names (monday–sunday).
- **`SlotOut`** — `id`, `slot_start`, `slot_end` (response for the availability endpoint).
- **`BookingRequest`** — `slot_id: int` (request body for `POST /appointments/book`).
- **`AppointmentOut`** — `id`, `status`, `slot_start`, `slot_end`, `doctor_name` (response for booking endpoint).

---

### Service

#### [NEW] `backend/app/services/scheduling.py`

`generate_slots_for_doctor(db, doctor_id, target_date) -> list[AppointmentSlot]`

Logic:
1. Load `DoctorProfile`; 404 if not found.
2. Validate `working_hours_config` against `WorkingHoursConfig` schema.
3. Look up the weekday entry — return `[]` if `null`/missing.
4. Walk `start` → `end` in `slot_duration_minutes` steps, building `(slot_start, slot_end)` pairs as timezone-aware UTC datetimes on `target_date`.
5. For each pair: attempt `db.add(AppointmentSlot(...))` + `db.flush()` inside a `try/except IntegrityError`. On `IntegrityError`: call `db.rollback()` on a savepoint so the outer session stays live, then continue. This makes the call **idempotent**.
6. `db.commit()` once at the end.
7. Re-query and return all `AppointmentSlot` rows for that `doctor_id` + `target_date`.

---

### API Endpoints

#### [MODIFY] `backend/app/api/scheduling.py` — [NEW FILE]

**`PATCH /doctors/me/working-hours`**
- Auth: `require_role("doctor")`
- Body: `WorkingHoursConfig`
- Loads the calling doctor's `DoctorProfile`, stores the validated JSON, commits.
- Returns the updated config.

**`POST /doctors/{doctor_id}/slots/generate?target_date=YYYY-MM-DD`**
- Auth: `require_role("doctor", "receptionist")`
- If caller is a `doctor`: assert `doctor_id` matches their own `doctor_profile.id` (403 otherwise — a doctor cannot generate for another doctor).
- Calls `generate_slots_for_doctor(db, doctor_id, target_date)`.
- Returns `list[SlotOut]`, status 201.

**`GET /slots?doctor_id=&date=YYYY-MM-DD`**
- Auth: `get_current_user` (any authenticated role)
- Query: `appointment_slots` LEFT JOIN `appointments` on `slot_id`, filter `appointments.id IS NULL`, filter by `doctor_id` and date range `[date 00:00, date+1 00:00)`, order by `slot_start ASC`.
- Returns `list[SlotOut]`. Returns `[]` (not an error) if no slots exist yet for that day.

**`POST /appointments/book`**
- Auth: `require_role("patient")`
- Body: `BookingRequest(slot_id: int)`
- Steps:
  1. Load `patient_profile` from `current_user.patient_profile`; 422 if not found.
  2. Fetch `AppointmentSlot` by `slot_id`; 404 if missing.
  3. Attempt `db.add(Appointment(patient_id=..., doctor_id=slot.doctor_id, slot_id=slot_id, status="booked"))` + `db.commit()`.
  4. On `IntegrityError`: inspect `str(exc.orig)` for the `uq_...slot_id` constraint name. If matched → `db.rollback()` + `HTTP 409 "This slot has just been booked by someone else — please choose another."`. Re-raise any other `IntegrityError` so real bugs surface.
  5. On success: refresh + return `AppointmentOut` (joined with slot for times, joined with doctor profile for name), status 201.
- `# TODO Module 7: receptionist walk-in booking` comment at top of function.

#### [MODIFY] `backend/app/main.py`
- Import and mount `scheduling_router` at prefix `""` (slots and appointments are top-level paths).

---

### Tests

#### [NEW] `backend/tests/test_scheduling.py`

**Fixtures used:**
- `authenticated_client(role=...)` from `conftest.py` — existing.
- A new **`authenticated_client_as(email, role)`** helper (inline in this test file, not in conftest — it registers a specific email so we can create two distinct patients for the concurrency test).

**Test cases:**

| ID | Name | Assertion |
|---|---|---|
| T1 | Working hours PATCH | 200, config stored correctly |
| T2 | Non-doctor cannot PATCH working hours | 403 |
| T3 | Slot generation creates correct count | `ceil((end - start) / slot_duration)` slots |
| T4 | Slot generation is idempotent | calling twice → same count, no duplicates |
| T5 | GET /slots returns only open slots | after booking one, it disappears from list |
| T6 | GET /slots returns [] for day with no generated slots | no error |
| T7 | Book nonexistent slot → 404 | |
| T8 | Book slot as doctor/receptionist → 403 | role guard verified |
| T9 | **Concurrency test (run 5×)** | exactly 1×201, exactly 1×409 per round |
| T10 | After concurrent booking, GET /slots excludes that slot | |

**Concurrency test design (T9):**
```python
import threading

results = []

def book(client):
    r = client.post("/appointments/book", json={"slot_id": slot_id})
    results.append(r.status_code)

t1 = threading.Thread(target=book, args=(patient1_client,))
t2 = threading.Thread(target=book, args=(patient2_client,))
t1.start(); t2.start()
t1.join(); t2.join()

assert sorted(results) == [201, 409]
```
Wrapped in `for _ in range(5)` with fresh slot each iteration.

**Patient fixtures for concurrency test:**
- **2 patient identities** needed — `patient1_client` and `patient2_client`, each registered with a distinct email and holding their own cookie jar.

---

## File Summary

| File | Action |
|---|---|
| `app/schemas/scheduling.py` | NEW |
| `app/services/__init__.py` | NEW (empty) |
| `app/services/scheduling.py` | NEW |
| `app/api/scheduling.py` | NEW |
| `app/main.py` | MODIFY — mount scheduling router |
| `tests/test_scheduling.py` | NEW |

---

## Verification Plan

### Automated Tests
```bash
DATABASE_URL=sqlite:// JWT_SECRET_KEY=test-secret .venv/bin/pytest tests/test_scheduling.py -v
```
All tests including T9 must pass across all 5 iterations of the concurrency loop.

Existing Module 2 tests must still pass:
```bash
DATABASE_URL=sqlite:// JWT_SECRET_KEY=test-secret .venv/bin/pytest tests/ -v
```

### Manual Verification (optional, with Docker running)
1. `POST /auth/register` as a doctor → `PATCH /doctors/me/working-hours` → `POST /doctors/1/slots/generate?target_date=2026-10-01` → `GET /slots?doctor_id=1&date=2026-10-01` → confirm list of open slots returned.
2. `POST /appointments/book` as a patient → confirm 201 and slot disappears from GET /slots.
