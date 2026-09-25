"""
Appointment State Machine service.

THIS IS THE ONLY PLACE IN THE CODEBASE PERMITTED TO WRITE appointments.status.

The initial INSERT in Module 3's book_appointment() passes status=AppointmentStatus.booked
to the Appointment() constructor — that is the initial creation, not a transition,
and is explicitly exempted from this rule.

Every subsequent status change — check-in, cancel, start-consultation, complete,
bill, pay — MUST go through transition_appointment(). No endpoint, no other service,
and no future module may do `appointment.status = <anything>` directly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import IllegalTransitionError
from app.models.appointment import Appointment, AppointmentStatus

if TYPE_CHECKING:
    from app.models.identity import User


# ── Legal Transitions Map ─────────────────────────────────────────────────────
# Encodes WRD §3.2 exactly. This map is COMPLETE and future-proof:
# - Transitions up to IN_CONSULTATION are handled by Module 4 endpoints.
# - COMPLETED, BILLING_PENDING, and PAID entries are wired here so the map
#   never needs to change when Modules 5 & 6 add their endpoints.
LEGAL_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.booked: {
        AppointmentStatus.checked_in,
        AppointmentStatus.cancelled,
        AppointmentStatus.no_show,
    },
    AppointmentStatus.checked_in: {
        AppointmentStatus.in_consultation,
        AppointmentStatus.cancelled,
    },
    AppointmentStatus.in_consultation: {
        AppointmentStatus.completed,
    },
    AppointmentStatus.completed: {
        AppointmentStatus.billing_pending,
    },
    AppointmentStatus.billing_pending: {
        AppointmentStatus.paid,
    },
    # Terminal states — no further transitions permitted.
    AppointmentStatus.cancelled: set(),
    AppointmentStatus.no_show: set(),
    AppointmentStatus.paid: set(),
}

# Columns that receive a timestamp stamp on a specific transition.
# Any status not listed here only touches updated_at (via SQLAlchemy onupdate).
_TIMESTAMP_COLUMNS: dict[AppointmentStatus, str] = {
    AppointmentStatus.checked_in: "checked_in_at",
    AppointmentStatus.in_consultation: "consultation_started_at",
    AppointmentStatus.completed: "completed_at",
}


# ── Central Transition Function ───────────────────────────────────────────────

def transition_appointment(
    db: Session,
    appointment_id: int,
    new_status: AppointmentStatus,
    actor: "User",
) -> Appointment:
    """Move an appointment to a new status, enforcing the legal-transitions map.

    Concerns this function handles:
    - Does the appointment exist? (404 if not)
    - Is the transition legal? (IllegalTransitionError if not)
    - Write the new status and the matching timestamp column.
    - Commit and return the refreshed appointment.

    Concerns this function does NOT handle (caller's responsibility):
    - Role/ownership authorisation (who is allowed to trigger this transition).
      That belongs at the endpoint layer so the two concerns stay separated.

    This is the ONLY place in the codebase permitted to write appointments.status.
    """
    appointment: Appointment | None = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment id={appointment_id} not found",
        )

    # Enforce legal-transitions table (WRD §3.2).
    current = appointment.status
    allowed = LEGAL_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise IllegalTransitionError(
            current_status=current,
            attempted_status=new_status,
            appointment_id=appointment_id,
        )

    # ── THE ONLY PERMITTED WRITE TO appointments.status ──────────────────────
    appointment.status = new_status  # noqa: guarded by LEGAL_TRANSITIONS check above

    # Set the matching lifecycle timestamp where applicable.
    ts_col = _TIMESTAMP_COLUMNS.get(new_status)
    if ts_col:
        setattr(appointment, ts_col, datetime.now(tz=timezone.utc))

    db.commit()
    db.refresh(appointment)
    return appointment
