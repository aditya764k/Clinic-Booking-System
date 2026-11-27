"""
Appointment State Machine API endpoints.

Endpoints
---------
POST  /appointments/{appointment_id}/check-in          → receptionist checks a patient in
POST  /appointments/{appointment_id}/cancel            → patient or receptionist cancels
POST  /appointments/{appointment_id}/start-consultation → doctor starts the consultation
GET   /appointments/queue/today                        → receptionist: all today's appointments
GET   /appointments/queue/mine                         → doctor: their own today's appointments

Routing note
------------
The static GET /appointments/queue/... routes are declared BEFORE the path-param
POST /appointments/{appointment_id}/... routes so FastAPI does not match the
literal string "queue" as an appointment_id integer parameter.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import IllegalTransitionError
from app.models.appointment import Appointment, AppointmentStatus
from app.models.identity import DoctorProfile, PatientProfile, User
from app.models.scheduling import AppointmentSlot
from app.schemas.billing import InvoiceOut
from app.schemas.scheduling import AppointmentOut, AppointmentQueueItem
from app.services.appointment_state import transition_appointment

logger = logging.getLogger(__name__)
router = APIRouter(tags=["appointments"])

# ── Status display order for queue sorting ────────────────────────────────────
_STATUS_ORDER: dict[str, int] = {
    AppointmentStatus.booked.value:          0,
    AppointmentStatus.checked_in.value:      1,
    AppointmentStatus.in_consultation.value: 2,
    AppointmentStatus.completed.value:       3,
    AppointmentStatus.billing_pending.value: 4,
    AppointmentStatus.paid.value:            5,
    AppointmentStatus.cancelled.value:       6,
    AppointmentStatus.no_show.value:         7,
}


def _status_val(appt: Appointment) -> str:
    return appt.status.value if hasattr(appt.status, "value") else str(appt.status)


def _appointment_out(appt: Appointment, slot: AppointmentSlot) -> AppointmentOut:
    """Build an AppointmentOut from an Appointment + its slot."""
    doctor_name = appt.doctor.full_name if appt.doctor else "Unknown"
    patient_name = appt.patient.full_name if appt.patient else "Unknown"
    return AppointmentOut(
        id=appt.id,
        status=_status_val(appt),
        slot_start=slot.slot_start,
        slot_end=slot.slot_end,
        doctor_name=doctor_name,
        patient_name=patient_name,
    )


def _build_invoice_out(appt: Appointment) -> Optional[InvoiceOut]:
    """Return a nested InvoiceOut for the appointment, or None if not yet billed."""
    # For queue items, we usually want the most relevant invoice.
    # We will pick the treatment_fee if it exists and is pending, otherwise booking_fee.
    if not appt.invoices:
        return None
        
    # Sort so that treatment_fee comes first, or just find pending ones
    pending_invoices = [i for i in appt.invoices if hasattr(i.status, "value") and i.status.value == "pending" or i.status == "pending"]
    inv = pending_invoices[0] if pending_invoices else appt.invoices[-1]
    
    if inv is None:
        return None
    return InvoiceOut(
        id=inv.id,
        appointment_id=inv.appointment_id,
        amount=inv.amount,
        currency=inv.currency,
        status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
        payment_method=(
            inv.payment_method.value
            if inv.payment_method and hasattr(inv.payment_method, "value")
            else inv.payment_method
        ),
        razorpay_order_id=inv.razorpay_order_id,
        cash_amount_received=inv.cash_amount_received,
        receipt_number=inv.receipt_number,
        collected_by_user_id=inv.collected_by_user_id,
        created_at=inv.created_at,
        paid_at=inv.paid_at,
    )


def _queue_item(appt: Appointment, slot: AppointmentSlot) -> AppointmentQueueItem:
    """Build an AppointmentQueueItem for queue responses, including nested invoice."""
    return AppointmentQueueItem(
        id=appt.id,
        status=_status_val(appt),
        patient_name=appt.patient.full_name if appt.patient else "Unknown",
        doctor_name=appt.doctor.full_name if appt.doctor else "Unknown",
        slot_start=slot.slot_start,
        slot_end=slot.slot_end,
        invoice=_build_invoice_out(appt),
    )


def _today_utc_range() -> tuple[datetime, datetime]:
    """Return (start_of_today_utc, start_of_tomorrow_utc) for date filtering.

    Matches the UTC-based date filtering convention used by Module 3's
    GET /slots endpoint (slot_start stored as UTC datetimes).
    """
    today = datetime.now(tz=timezone.utc).date()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


# ── Static GET routes first (prevents FastAPI matching "queue" as an int param) ─

@router.get(
    "/appointments/queue/today",
    response_model=List[AppointmentQueueItem],
)
def receptionist_queue_today(
    target_date: Optional[date] = Query(
        default=None,
        alias="date",
        description="YYYY-MM-DD; defaults to UTC today if omitted",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """FR-REC-01: All appointments for today, sorted by lifecycle order.

    Returns a flat list sorted by status lifecycle order (booked first,
    terminal states last). Matches the existing flat-list response convention.
    """
    if target_date is not None:
        start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
    else:
        start, end = _today_utc_range()
        
    appointments: list[Appointment] = (
        db.query(Appointment)
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
        .filter(AppointmentSlot.slot_start >= start)
        .filter(AppointmentSlot.slot_start < end)
        .all()
    )

    items = []
    for appt in appointments:
        slot = db.get(AppointmentSlot, appt.slot_id)
        if slot:
            items.append(_queue_item(appt, slot))

    items.sort(key=lambda x: _STATUS_ORDER.get(x.status, 99))
    return items


@router.get(
    "/appointments/queue/mine",
    response_model=List[AppointmentQueueItem],
)
def my_queue(
    target_date: Optional[date] = Query(
        default=None,
        alias="date",
        description="YYYY-MM-DD; defaults to today",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "patient")),
) -> Any:
    """Get appointments for the currently authenticated user (doctor or patient)."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    if role_val == "doctor":
        profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if profile is None:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        query_filter = (Appointment.doctor_id == profile.id)
    else:
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if profile is None:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        query_filter = (Appointment.patient_id == profile.id)

    query = db.query(Appointment).join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id).filter(query_filter)

    if target_date is not None:
        start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        query = query.filter(AppointmentSlot.slot_start >= start, AppointmentSlot.slot_start < end)
    elif role_val == "doctor":
        # Doctors default to today to avoid loading entire history
        target_date = datetime.now(tz=timezone.utc).date()
        start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        query = query.filter(AppointmentSlot.slot_start >= start, AppointmentSlot.slot_start < end)
    # Patients fetch all history/upcoming if no date is provided.

    appointments: list[Appointment] = query.all()

    items = []
    for appt in appointments:
        slot = db.get(AppointmentSlot, appt.slot_id)
        if slot:
            items.append(_queue_item(appt, slot))

    items.sort(key=lambda x: _STATUS_ORDER.get(x.status, 99))
    return items


# ── Transition endpoints (path-param routes after static routes) ──────────────

@router.post(
    "/appointments/{appointment_id}/check-in",
    response_model=AppointmentOut,
)
def check_in(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """FR-REC-02: Receptionist checks a patient in.

    Delegates entirely to transition_appointment(); any IllegalTransitionError
    is handled by the FastAPI exception handler in main.py — not caught here.
    """
    appt = transition_appointment(
        db, appointment_id, AppointmentStatus.checked_in, actor=current_user
    )
    slot = db.get(AppointmentSlot, appt.slot_id)
    return _appointment_out(appt, slot)


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentOut,
)
def cancel(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient", "receptionist")),
) -> Any:
    """FR-PAT-05: Patient or receptionist cancels an appointment.

    Ownership rule: if caller is a patient they may only cancel their OWN
    appointments. Receptionists can cancel any appointment.
    """
    role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role)
    )

    if role_val == "patient":
        # Resolve the patient's profile to compare against appointment.patient_id
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
        # Fetch the appointment to check ownership (before calling transition so
        # we return a 403 rather than a 404 when both conditions are violated)
        appt_check: Appointment | None = db.get(Appointment, appointment_id)
        if appt_check is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment id={appointment_id} not found",
            )
        if appt_check.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own appointments",
            )

    appt = transition_appointment(
        db, appointment_id, AppointmentStatus.cancelled, actor=current_user
    )
    slot = db.get(AppointmentSlot, appt.slot_id)
    return _appointment_out(appt, slot)


@router.post(
    "/appointments/{appointment_id}/start-consultation",
    response_model=AppointmentOut,
)
def start_consultation(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
) -> Any:
    """FR-DOC-02: Doctor marks an appointment as in-consultation.

    Ownership rule: a doctor may only start a consultation on their OWN
    appointments. Attempting to start another doctor's appointment is a hard
    403 — this is a business rule, not a convenience check.
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

    # Ownership check: fetch appointment first to return 403 before 404 ambiguity
    appt_check: Appointment | None = db.get(Appointment, appointment_id)
    if appt_check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment id={appointment_id} not found",
        )
    if appt_check.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only start consultations for your own patients",
        )

    # Concurrency guard: A doctor can only have one active consultation at a time
    active_consultation = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == doctor.id)
        .filter(Appointment.status == AppointmentStatus.in_consultation)
        .first()
    )
    if active_consultation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active consultation. Please complete it before starting a new one.",
        )

    appt = transition_appointment(
        db, appointment_id, AppointmentStatus.in_consultation, actor=current_user
    )
    slot = db.get(AppointmentSlot, appt.slot_id)
    return _appointment_out(appt, slot)
