# Module 4: Appointment State Machine

## Background

Modules 1–3 are complete. The key facts from the codebase scan:

- `AppointmentStatus` enum lives at `backend/app/models/appointment.py:21` — values: `booked`, `checked_in`, `in_consultation`, `completed`, `billing_pending`, `paid`, `cancelled`, `no_show`.
- `Appointment` model has timestamp columns: `checked_in_at`, `consultation_started_at`, `completed_at`. `updated_at` is auto-updated via `onupdate`.
- No custom exception classes exist yet in `app/core/` — `app/core/` contains only `config.py`, `database.py`, `dependencies.py`, `security.py`.
- No FastAPI exception handlers are registered in `app/main.py` beyond HTTP defaults.
- Auth pattern: `require_role("doctor")` / `require_role("patient", "receptionist")` dependency factory in `app/core/dependencies.py`.
- Date filtering in Module 3 uses `timezone.utc` naive UTC datetimes for slot_start comparisons.
- Response convention: flat `AppointmentOut` model in `app/schemas/scheduling.py` (not a grouped dict). We'll extend this pattern.
- Services go in `app/services/` (Module 3's `scheduling.py` is the existing example).
- APIs go in `app/api/` and are mounted in `app/main.py`.

## Key Design Decisions

> [!IMPORTANT]
> The ONLY code path allowed to write `appointment.status` is `transition_appointment()` in `app/services/appointment_state.py`. The Module 3 booking code sets `status=AppointmentStatus.booked` at `Appointment()` constructor time (INSERT) — this is the initial creation, not a transition, and is explicitly exempted. All other status changes go through `transition_appointment()`.

> [!NOTE]
> Queue endpoints return a **flat sorted list** (not a grouped dict) to match the existing `AppointmentOut` shape. The list is sorted by a status-order key. Each item includes: `appointment_id`, `patient_name`, `doctor_name`, `slot_start`, `slot_end`, `status`.

---

## Proposed Changes

### 1. Domain Exception

#### [NEW] `backend/app/core/exceptions.py`
```python
class IllegalTransitionError(Exception):
    def __init__(self, current_status, attempted_status, appointment_id):
        ...  # __str__ → "Cannot transition appointment {id} from '{cur}' to '{att}'"
```

#### [MODIFY] `backend/app/main.py`
- Register a FastAPI `exception_handler` for `IllegalTransitionError`:
  ```python
  @app.exception_handler(IllegalTransitionError)
  async def illegal_transition_handler(request, exc):
      return JSONResponse(status_code=409, content={
          "detail": str(exc),
          "current_status": exc.current_status.value,
          "attempted_status": exc.attempted_status.value,
      })
  ```

---

### 2. Legal Transitions Map + Central Function

#### [NEW] `backend/app/services/appointment_state.py`

**`LEGAL_TRANSITIONS`** constant (complete, future-proof — Modules 5/6 add the *endpoints* for COMPLETED/BILLING_PENDING/PAID, but the map is fully wired here):

```python
LEGAL_TRANSITIONS = {
    AppointmentStatus.booked:          {AppointmentStatus.checked_in, AppointmentStatus.cancelled, AppointmentStatus.no_show},
    AppointmentStatus.checked_in:      {AppointmentStatus.in_consultation, AppointmentStatus.cancelled},
    AppointmentStatus.in_consultation: {AppointmentStatus.completed},
    AppointmentStatus.completed:       {AppointmentStatus.billing_pending},
    AppointmentStatus.billing_pending: {AppointmentStatus.paid},
    AppointmentStatus.cancelled:       set(),
    AppointmentStatus.no_show:         set(),
    AppointmentStatus.paid:            set(),
}
```

**`transition_appointment(db, appointment_id, new_status, actor)`**:
1. `db.get(Appointment, appointment_id)` → HTTPException 404 if missing.
2. Check `new_status in LEGAL_TRANSITIONS[appt.status]` → raise `IllegalTransitionError` if not.
3. `appt.status = new_status` (the ONLY place this is permitted — code comment).
4. Set timestamp columns: `checked_in_at` for `checked_in`, `consultation_started_at` for `in_consultation`, `completed_at` for `completed`.
5. `db.commit(); db.refresh(appt); return appt`.

---

### 3. New Schemas

#### [MODIFY] `backend/app/schemas/scheduling.py`
- Extend `AppointmentOut` to add `patient_name: str | None = None` (needed for queue endpoints).
- Add `AppointmentQueueItem` schema for queue responses: `id`, `status`, `patient_name`, `doctor_name`, `slot_start`, `slot_end`.

---

### 4. New API Endpoints

#### [NEW] `backend/app/api/appointment_state.py`

All under a new `router = APIRouter(tags=["appointments"])`.

| Method | Path | Auth | Ownership check |
|--------|------|------|-----------------|
| `POST` | `/appointments/{id}/check-in` | `receptionist` | None |
| `POST` | `/appointments/{id}/cancel` | `patient`, `receptionist` | Patient: own appointments only |
| `POST` | `/appointments/{id}/start-consultation` | `doctor` | Own patients only |
| `GET` | `/appointments/queue/today` | `receptionist` | None (all doctors) |
| `GET` | `/appointments/queue/mine` | `doctor` | Own appointments only |

**Queue sort order**: `booked=0, checked_in=1, in_consultation=2, completed=3, billing_pending=4, paid=5, cancelled=6, no_show=7`

#### [MODIFY] `backend/app/main.py`
- Import and mount `appointment_state_router`.

> [!WARNING]
> The GET `/appointments/queue/today` and GET `/appointments/queue/mine` routes must be mounted BEFORE any path-parameter route like `/appointments/{id}/...` to prevent FastAPI from matching `queue` as an `appointment_id`. We'll handle this by placing static-path GET routes at the top of the router.

---

### 5. Tests

#### [NEW] `backend/tests/test_appointment_state.py`

Uses the existing `authenticated_client`, `client`, `db_session` fixtures from `conftest.py` plus a new `make_role_client` helper (same pattern as `test_scheduling.py`).

**Test coverage:**

| Group | Description |
|---|---|
| **Legal transitions matrix** | For every `(from, to)` in `LEGAL_TRANSITIONS` — seed appointment, call endpoint, assert 200 + correct timestamp set |
| **Illegal transitions** | Programmatically enumerate all `(from, to)` NOT in legal map; assert 409 + `IllegalTransitionError` detail |
| **RBAC guards** | Patient/doctor → check-in: 403; patient/receptionist → start-consultation: 403 |
| **Ownership guards** | Wrong doctor → start-consultation: 403; patient → cancel another patient's appt: 403 |
| **Queue correctness** | Receptionist queue returns today's appointments only; doctor queue never leaks other doctor's data |
| **E2E HTTP guard** | call check-in twice → second returns 409 from handler; call start-consultation on booked (not checked_in) → 409 |

---

## File Summary

| File | Action |
|---|---|
| `app/core/exceptions.py` | NEW |
| `app/services/appointment_state.py` | NEW |
| `app/schemas/scheduling.py` | MODIFY (extend AppointmentOut, add QueueItem) |
| `app/api/appointment_state.py` | NEW |
| `app/main.py` | MODIFY (add exception handler + mount router) |
| `tests/test_appointment_state.py` | NEW |

## Verification Plan

```bash
DATABASE_URL=sqlite:// JWT_SECRET_KEY=test-secret-key-for-ci-only \
  .venv/bin/pytest tests/test_appointment_state.py -v
```

Full regression:
```bash
DATABASE_URL=sqlite:// JWT_SECRET_KEY=test-secret-key-for-ci-only \
  .venv/bin/pytest tests/ -v
```
All 43 existing tests + all new Module 4 tests must pass.
