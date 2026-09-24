"""
Scheduling & Availability API endpoints.

Endpoints
---------
PATCH  /doctors/me/working-hours          → set/update doctor's schedule config
POST   /doctors/{doctor_id}/slots/generate → generate slots for a date
GET    /slots                              → list open slots for a doctor+date
POST   /appointments/book                  → patient books an open slot

Concurrency guarantee
---------------------
POST /appointments/book does NOT do a pre-check SELECT to see if the slot is
free. The UNIQUE constraint on appointments.slot_id is the actual race guard.
The optional existence check in step 2 (fetch slot → 404) is for UX only;
the INSERT's IntegrityError is the authoritative source of truth.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, InvalidRequestError, OperationalError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.appointment import Appointment, AppointmentStatus
from app.models.identity import DoctorProfile, PatientProfile, User
from app.models.scheduling import AppointmentSlot
from app.schemas.scheduling import (
    AppointmentOut,
    BookingRequest,
    SlotOut,
    WorkingHoursConfig,
)
from app.services.scheduling import generate_slots_for_doctor

logger = logging.getLogger(__name__)
router = APIRouter(tags=["scheduling"])


# ── Working Hours Config ──────────────────────────────────────────────────────

@router.patch("/doctors/me/working-hours", response_model=WorkingHoursConfig)
def update_working_hours(
    body: WorkingHoursConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
) -> Any:
    """Set or update the calling doctor's working-hours configuration.

    Stores the validated JSON in ``doctor_profiles.working_hours_config``.
    Only the doctor themselves can update their own schedule.
    """
    doctor: DoctorProfile | None = (
        db.query(DoctorProfile)
        .filter(DoctorProfile.user_id == current_user.id)
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for current user",
        )

    doctor.working_hours_config = body.model_dump()
    db.commit()
    db.refresh(doctor)
    return WorkingHoursConfig.model_validate(doctor.working_hours_config)


# ── Slot Generation ───────────────────────────────────────────────────────────

@router.post(
    "/doctors/{doctor_id}/slots/generate",
    response_model=List[SlotOut],
    status_code=status.HTTP_201_CREATED,
)
def generate_slots(
    doctor_id: int,
    target_date: date = Query(..., description="Date to generate slots for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "receptionist")),
) -> Any:
    """Generate appointment slots for a doctor on a given date.

    - A ``doctor`` caller can only generate slots for their own profile.
    - A ``receptionist`` can generate slots on behalf of any doctor.
    - Idempotent: calling twice for the same doctor+date is safe.
    """
    role_str = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role)
    )

    if role_str == "doctor":
        # Verify the doctor is generating for themselves only
        own_profile: DoctorProfile | None = (
            db.query(DoctorProfile)
            .filter(DoctorProfile.user_id == current_user.id)
            .first()
        )
        if own_profile is None or own_profile.id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors may only generate slots for their own profile",
            )

    slots = generate_slots_for_doctor(db, doctor_id, target_date)
    return [SlotOut.model_validate(s) for s in slots]


# ── Availability (Open Slots) ─────────────────────────────────────────────────

@router.get("/slots", response_model=List[SlotOut])
def list_open_slots(
    doctor_id: int = Query(..., description="Doctor profile ID"),
    date: date = Query(..., description="Date to query (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List open (unbooked) appointment slots for a doctor on a given date.

    Returns an empty list if no slots have been generated yet — never errors.
    Does NOT auto-generate slots; generation is an explicit separate action.

    A slot is "open" when it has no linked Appointment row (LEFT JOIN + IS NULL).
    """
    day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    open_slots = (
        db.query(AppointmentSlot)
        .outerjoin(Appointment, Appointment.slot_id == AppointmentSlot.id)
        .filter(
            AppointmentSlot.doctor_id == doctor_id,
            AppointmentSlot.slot_start >= day_start,
            AppointmentSlot.slot_start < day_end,
            Appointment.id.is_(None),  # no linked appointment → open slot
        )
        .order_by(AppointmentSlot.slot_start.asc())
        .all()
    )

    return [SlotOut.model_validate(s) for s in open_slots]


# ── Booking ───────────────────────────────────────────────────────────────────

@router.post(
    "/appointments/book",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    body: BookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient")),
) -> Any:
    """Book an open appointment slot for the currently authenticated patient.

    # TODO Module 7: receptionist walk-in booking on behalf of a patient.

    Concurrency safety
    ------------------
    We do NOT pre-check whether the slot is free with a SELECT and rely on
    that result — that's a check-then-act race condition. Instead we attempt
    the INSERT directly. The UNIQUE constraint on appointments.slot_id is the
    authoritative guard: only one INSERT can win. The loser gets an
    IntegrityError which we convert to HTTP 409.
    """
    # Step 1: Get the patient's profile
    patient: PatientProfile | None = (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No patient profile found for current user",
        )

    # Step 2: Fetch the slot (UX-only check — 404 if slot doesn't exist at all)
    slot: AppointmentSlot | None = db.get(AppointmentSlot, body.slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot id={body.slot_id} does not exist",
        )

    # Step 3: Attempt the INSERT — let the DB constraint handle the race.
    # We capture slot times BEFORE adding to the session so we don't need to
    # re-query them after a potential rollback.
    slot_start = slot.slot_start
    slot_end = slot.slot_end
    slot_doctor_id = slot.doctor_id

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=slot_doctor_id,
        slot_id=slot.id,
        status=AppointmentStatus.booked,
    )
    db.add(appointment)

    try:
        db.commit()
    except (IntegrityError, OperationalError, InvalidRequestError) as exc:
        db.rollback()
        exc_orig = getattr(exc, "orig", None)
        exc_str = str(exc_orig).lower() if exc_orig else str(exc).lower()
        # Detect the specific slot_id unique constraint violation.
        # SQLite:     "unique constraint failed: appointments.slot_id"
        # PostgreSQL: "duplicate key value violates unique constraint ..."
        # OperationalError: SQLite 'database is locked' under high concurrency
        # InvalidRequestError: SQLite race — ORM loses the new row's PK ("null identity key")
        slot_conflict = (
            "slot_id" in exc_str
            or "uq_appointments_slot_id" in exc_str
            or "appointments.slot_id" in exc_str
            or (("unique" in exc_str or "duplicate" in exc_str) and "slot" in exc_str)
            or "database is locked" in exc_str
            or "null identity key" in exc_str
            or isinstance(exc, InvalidRequestError)
        )
        if slot_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This slot has just been booked by someone else \u2014 please choose another.",
            )
        # Re-raise any other error so real bugs surface
        raise

    # Success path — use a fresh query to avoid stale ORM state
    saved = db.get(Appointment, appointment.id)

    # Load doctor name for response
    doctor: DoctorProfile = db.get(DoctorProfile, slot_doctor_id)
    doctor_name = doctor.full_name if doctor else "Unknown"

    return AppointmentOut(
        id=saved.id,
        status=saved.status.value if hasattr(saved.status, "value") else str(saved.status),
        slot_start=slot_start,
        slot_end=slot_end,
        doctor_name=doctor_name,
    )
