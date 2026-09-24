"""
Scheduling service: slot generation logic.

Design notes
------------
- generate_slots_for_doctor is IDEMPOTENT.  Calling it twice for the same
  doctor+date must not error or create duplicate rows.  This is achieved by
  wrapping each INSERT in a savepoint and catching IntegrityError per-row
  (the unique constraint on (doctor_id, slot_start) rejects duplicates).
  Works identically on SQLite (tests) and PostgreSQL (production).

- Timezone handling: working_hours_config stores naive "HH:MM" strings.
  We combine them with target_date and treat the result as UTC (timezone=UTC).
  In a production system you would combine with the doctor's local timezone;
  UTC is acceptable here because the spec doesn't require tz conversion.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.identity import DoctorProfile
from app.models.scheduling import AppointmentSlot
from app.schemas.scheduling import WorkingHoursConfig

logger = logging.getLogger(__name__)

# Map Python weekday() int → config key name
_WEEKDAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


def generate_slots_for_doctor(
    db: Session,
    doctor_id: int,
    target_date: date,
) -> List[AppointmentSlot]:
    """Generate AppointmentSlot rows for *doctor_id* on *target_date*.

    - Reads ``DoctorProfile.working_hours_config``.
    - Skips days marked ``null`` or not present in config.
    - Inserts slots idempotently: duplicate (doctor_id, slot_start) rows are
      silently skipped via savepoint + IntegrityError catch.
    - Returns the full list of slots for that doctor+date (new + pre-existing).

    Raises ``HTTP 404`` if doctor not found.
    Raises ``HTTP 422`` if working_hours_config is missing or invalid.
    """
    doctor: DoctorProfile | None = db.get(DoctorProfile, doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with id={doctor_id} not found",
        )

    raw_config = doctor.working_hours_config
    if not raw_config:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Doctor has no working_hours_config set. "
                   "Call PATCH /doctors/me/working-hours first.",
        )

    try:
        config = WorkingHoursConfig.model_validate(raw_config)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Doctor's working_hours_config is invalid: {exc}",
        )

    weekday_name = _WEEKDAY_NAMES[target_date.weekday()]
    day_schedule = config.schedule.get(weekday_name)

    if day_schedule is None:
        # Doctor doesn't work on this day — return whatever already exists
        return _query_slots_for_date(db, doctor_id, target_date)

    # Build (slot_start, slot_end) pairs
    start_h, start_m = int(day_schedule.start[:2]), int(day_schedule.start[3:])
    end_h, end_m = int(day_schedule.end[:2]), int(day_schedule.end[3:])

    current = datetime(
        target_date.year, target_date.month, target_date.day,
        start_h, start_m, tzinfo=timezone.utc,
    )
    end_dt = datetime(
        target_date.year, target_date.month, target_date.day,
        end_h, end_m, tzinfo=timezone.utc,
    )
    delta = timedelta(minutes=config.slot_duration_minutes)

    inserted = 0
    skipped = 0

    while current + delta <= end_dt:
        slot_start = current
        slot_end = current + delta

        # Use a savepoint so a duplicate doesn't kill the whole transaction
        try:
            # nested() creates a SAVEPOINT on PostgreSQL / a nested transaction on SQLite
            with db.begin_nested():
                db.add(AppointmentSlot(
                    doctor_id=doctor_id,
                    slot_start=slot_start,
                    slot_end=slot_end,
                ))
            inserted += 1
        except IntegrityError:
            # Duplicate (doctor_id, slot_start) — already exists, skip silently
            skipped += 1

        current += delta

    db.commit()
    logger.info(
        "generate_slots_for_doctor: doctor_id=%d date=%s inserted=%d skipped=%d",
        doctor_id, target_date, inserted, skipped,
    )

    return _query_slots_for_date(db, doctor_id, target_date)


def _query_slots_for_date(
    db: Session,
    doctor_id: int,
    target_date: date,
) -> List[AppointmentSlot]:
    """Return all AppointmentSlot rows for a doctor on a given date."""
    day_start = datetime(target_date.year, target_date.month, target_date.day,
                         tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    return (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.doctor_id == doctor_id,
            AppointmentSlot.slot_start >= day_start,
            AppointmentSlot.slot_start < day_end,
        )
        .order_by(AppointmentSlot.slot_start)
        .all()
    )
