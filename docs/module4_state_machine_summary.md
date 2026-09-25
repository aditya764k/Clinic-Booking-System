# Module 4: Appointment State Machine & Queues

This document summarizes the architecture, design patterns, and business logic implemented in Module 4 for managing the lifecycle of appointments.

## Core Architectural Concept: The Centralized Guard

The most critical design decision in Module 4 is the **Centralized Guard Pattern** for state transitions. 

In many CRUD applications, state changes are scattered across various endpoints (e.g., `appointment.status = "checked_in"` in the check-in route, `appointment.status = "cancelled"` in the cancel route). This leads to duplicated validation logic and easily missed edge cases (like cancelling an already-completed appointment).

Module 4 solves this by centralizing all status updates into a single service function: `transition_appointment()` in `app/services/appointment_state.py`.

**The Golden Rule:**
No endpoint, service, or future module is permitted to write to `appointments.status` directly. Every change after the initial booking (which is an `INSERT`) must pass through `transition_appointment()`.

### The `LEGAL_TRANSITIONS` Matrix
The state machine is driven by a hardcoded dictionary that defines exactly which states can move to which other states. 

```python
LEGAL_TRANSITIONS = {
    AppointmentStatus.booked: {AppointmentStatus.checked_in, AppointmentStatus.cancelled, AppointmentStatus.no_show},
    AppointmentStatus.checked_in: {AppointmentStatus.in_consultation, AppointmentStatus.cancelled},
    # ...
}
```
*Note: This matrix includes terminal states (Completed, Paid, etc.) that belong to future modules (5 & 6). This future-proofs the state machine so its core logic won't need rewriting later.*

## Domain Exceptions vs. HTTP Transport

To keep the service layer clean and framework-agnostic, we implemented a custom domain exception.

1. **`IllegalTransitionError` (Domain Layer)**: Raised by `transition_appointment()` if a requested state change violates the `LEGAL_TRANSITIONS` matrix. It knows nothing about HTTP status codes.
2. **Global Exception Handler (HTTP Layer)**: In `app/main.py`, we registered a FastAPI `@app.exception_handler(IllegalTransitionError)`. This automatically catches the domain exception globally and translates it into a standard HTTP 409 Conflict JSON response.

This separation of concerns means our core business logic doesn't depend on FastAPI imports, making it easier to test and maintain.

## Security: RBAC vs. Data Ownership

Module 4 carefully separates two distinct security concepts across the new endpoints (`/check-in`, `/cancel`, `/start-consultation`):

1. **Role-Based Access Control (RBAC)**: "Is this user a doctor?" 
   - Handled cleanly via the existing FastAPI dependency injection: `Depends(require_role("doctor"))`.
2. **Data Ownership**: "Is this user *the specific doctor assigned to this appointment*?"
   - Handled inside the endpoint body *before* calling the transition function. We fetch the appointment, check `appointment.doctor_id == current_user_doctor_profile.id`, and raise an HTTP 403 Forbidden if it fails.

By separating these, the `transition_appointment` function doesn't need to know about HTTP contexts or JWT tokens—it just trusts that if it is called, the caller has the right to attempt the transition.

## Queue Endpoints & Date Filtering

We implemented two queue endpoints:
- `GET /appointments/queue/today` (Receptionist - sees all clinic appointments)
- `GET /appointments/queue/mine` (Doctor - sees only their own appointments)

**Key Logic:**
- **UTC Date Boundaries**: Because slots are stored as timezone-aware UTC datetimes, filtering "today" requires calculating the exact UTC midnight boundaries for the target date (`start` <= slot_start < `end`).
- **Lifecycle Sorting**: Instead of returning a grouped dictionary, the queue returns a flat list sorted by the natural lifecycle of an appointment (`booked` -> `checked_in` -> `in_consultation`, etc.). This was achieved by defining a `_STATUS_ORDER` dictionary map and sorting the result set in Python before returning it.
- **Route Ordering**: In `app/api/appointment_state.py`, the static GET routes for the queues are defined *above* the path-parameter POST routes (like `/appointments/{appointment_id}/check-in`) to prevent FastAPI's router from mistaking the word "queue" for an `appointment_id`.

## Testing Strategy
The integration test suite (`tests/test_appointment_state.py`) was entirely rewritten to ensure complete isolation between test clients.

- **Fixture Isolation**: Replaced a shared whoami-based profile lookup with a `register_user` helper that returns the `profile_id` immediately upon registration. This ensures cookies don't cross-contaminate when testing multi-actor scenarios (e.g., Doctor 1 trying to start Doctor 2's consultation).
- **Matrix Generation**: The illegal transition tests dynamically generate every possible invalid `(from, to)` status pair by subtracting the `LEGAL_TRANSITIONS` map from all possible combinations, ensuring 100% coverage without manually maintaining a huge list.
- **E2E HTTP Guards**: Tests explicitly verify that hitting the endpoints (not just the service functions) with invalid transitions results in the expected HTTP 409 responses, proving the global exception handler is correctly wired.
