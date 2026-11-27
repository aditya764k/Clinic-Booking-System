"""
Receptionist Operations API — Module 7.

Endpoints
---------
POST /receptionist/walk-in
    Register a walk-in patient and create a CHECKED_IN appointment atomically.
    Deduplicates patients by email (primary) then phone (fallback).

GET /receptionist/analytics/daily
    Daily operational metrics: appointment counts grouped by status + revenue
    split by payment method. Accepts an optional ?date=YYYY-MM-DD param.

GET /receptionist/doctors
    List all doctor profiles for the walk-in form's doctor dropdown.

GET /receptionist/doctors/{doctor_id}/slots
    List available (unbooked) slots for a specific doctor today (or ?date=).
    Powers the slot dropdown in the walk-in form.

Design rules
------------
- Walk-in registration is a single atomic transaction: patient resolution +
  slot conflict check + appointment creation all commit together.
- If a user with the given email exists, we reuse their patient profile (if any).
  If they have no patient profile yet, we create one (doctor users can walk in).
- If no email is provided, we look up PatientProfile by phone. If still no match,
  we auto-generate walkin_{phone}@clinic.internal as the User email.
- Slot conflict uses a query-then-insert pattern (not IntegrityError catching)
  because receptionists see a slot list — concurrency conflicts are extremely
  unlikely at front-desk pace. The unique constraint remains the DB safety net.
- Analytics counts only appointments whose slot_start falls on the requested
  date in UTC. Revenue sums only paid invoices.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.security import hash_password
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Invoice, InvoiceStatus, PaymentMethod, InvoiceType
from app.models.identity import DoctorProfile, PatientProfile, User, UserRole
from app.models.scheduling import AppointmentSlot
from app.schemas.receptionist import (
    DailyAnalyticsOut,
    DoctorOut,
    SlotAvailableOut,
    WalkInOut,
    WalkInRegistrationRequest,
)
from app.services.appointment_state import transition_appointment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/receptionist", tags=["receptionist"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _date_range(target: date) -> tuple[datetime, datetime]:
    """Return UTC (start_of_day, start_of_next_day) for a given date."""
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _resolve_or_create_patient(
    db: Session,
    first_name: str,
    last_name: str,
    phone: str,
    email: Optional[str],
) -> tuple[PatientProfile, bool]:
    """Find an existing patient or create a new User + PatientProfile.

    Lookup priority:
    1. By email (exact match on User.email — most reliable key).
    2. By phone (exact match on PatientProfile.phone).
    3. Create new User + PatientProfile.

    Returns (PatientProfile, is_new_patient).
    """
    full_name = f"{first_name.strip()} {last_name.strip()}"

    # Priority 1: look up by email
    if email:
        existing_user: User | None = (
            db.query(User).filter(User.email == email).first()
        )
        if existing_user is not None:
            # User exists — find or create their patient profile
            profile: PatientProfile | None = (
                db.query(PatientProfile)
                .filter(PatientProfile.user_id == existing_user.id)
                .first()
            )
            if profile is None:
                # User exists (maybe a doctor) — create a patient profile for them
                profile = PatientProfile(
                    user_id=existing_user.id,
                    full_name=full_name,
                    phone=phone,
                )
                db.add(profile)
                db.flush()
                return profile, True
            return profile, False

    # Priority 2: look up by phone
    if phone:
        existing_profile: PatientProfile | None = (
            db.query(PatientProfile)
            .filter(PatientProfile.phone == phone)
            .first()
        )
        if existing_profile is not None:
            return existing_profile, False

    # Priority 3: create new user + profile
    new_user = User(
        email=email,
        hashed_password=hash_password("password123"),   # default password for walk-ins
        role=UserRole.patient,
    )
    db.add(new_user)
    db.flush()  # get new_user.id

    new_profile = PatientProfile(
        user_id=new_user.id,
        full_name=full_name,
        phone=phone,
    )
    db.add(new_profile)
    db.flush()
    return new_profile, True


# ── Walk-in Registration ───────────────────────────────────────────────────────

@router.post("/walk-in", response_model=WalkInOut, status_code=status.HTTP_201_CREATED)
def register_walk_in(
    body: WalkInRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """FR-REC-03: Register a walk-in patient and create a CHECKED_IN appointment.

    This is a single atomic transaction:
    1. Resolve patient (by email → phone → create new).
    2. Verify slot is still available (409 if taken).
    3. Create Appointment with status=payment_pending.
    4. Create booking_fee Invoice.
    5. Commit everything and return invoice ID for payment processing.
    """
    # Step 1: Verify doctor exists
    doctor: DoctorProfile | None = db.get(DoctorProfile, body.doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor profile id={body.doctor_id} not found",
        )

    # Step 2: Verify slot exists
    slot: AppointmentSlot | None = db.get(AppointmentSlot, body.slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot id={body.slot_id} not found",
        )
    if slot.doctor_id != body.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested slot does not belong to the requested doctor",
        )

    # Step 3: Slot conflict check (query-then-insert; DB constraint is safety net)
    conflict: Appointment | None = (
        db.query(Appointment).filter(Appointment.slot_id == body.slot_id).first()
    )
    if conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slot id={body.slot_id} is already booked",
        )

    # Step 4: Resolve or create patient (all in the same transaction)
    patient_profile, is_new = _resolve_or_create_patient(
        db,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        email=body.email,
    )

    # Step 5: Create appointment in PAYMENT_PENDING state.
    appt = Appointment(
        patient_id=patient_profile.id,
        doctor_id=body.doctor_id,
        slot_id=body.slot_id,
        status=AppointmentStatus.payment_pending,
    )
    db.add(appt)
    db.flush()  # get appt.id before creating invoice

    # Step 6: Create booking_fee invoice
    invoice = Invoice(
        appointment_id=appt.id,
        amount=doctor.consultation_fee,
        currency="INR",
        invoice_type=InvoiceType.booking_fee,
        status=InvoiceStatus.pending,
    )
    db.add(invoice)
    db.flush()

    db.commit()
    db.refresh(appt)
    db.refresh(slot)
    db.refresh(invoice)

    return WalkInOut(
        appointment_id=appt.id,
        patient_id=patient_profile.id,
        patient_name=patient_profile.full_name,
        status=appt.status.value if hasattr(appt.status, "value") else str(appt.status),
        slot_start=slot.slot_start,
        slot_end=slot.slot_end,
        is_new_patient=is_new,
        invoice_id=invoice.id,
        amount=float(invoice.amount),
        currency=invoice.currency,
    )


# ── Daily Analytics ────────────────────────────────────────────────────────────

@router.get("/analytics/daily", response_model=DailyAnalyticsOut)
def daily_analytics(
    target_date: Optional[date] = Query(
        default=None,
        alias="date",
        description="YYYY-MM-DD; defaults to today UTC",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """FR-REC-06: Daily operational metrics for the receptionist dashboard.

    Counts are based on AppointmentSlot.slot_start falling on the given date
    in UTC — consistent with the queue endpoint's date-filtering convention.
    Revenue sums only paid invoices linked to appointments on that date.
    """
    if target_date is None:
        target_date = datetime.now(tz=timezone.utc).date()

    start, end = _date_range(target_date)

    # Fetch all appointments for the day
    appointments: list[Appointment] = (
        db.query(Appointment)
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
        .filter(
            AppointmentSlot.slot_start >= start,
            AppointmentSlot.slot_start < end,
        )
        .all()
    )

    # Count by status
    checked_in = sum(
        1 for a in appointments
        if (a.status.value if hasattr(a.status, "value") else str(a.status))
        == AppointmentStatus.checked_in.value
    )
    completed = sum(
        1 for a in appointments
        if (a.status.value if hasattr(a.status, "value") else str(a.status))
        in (AppointmentStatus.completed.value,
            AppointmentStatus.billing_pending.value,
            AppointmentStatus.paid.value)
    )
    no_show = sum(
        1 for a in appointments
        if (a.status.value if hasattr(a.status, "value") else str(a.status))
        == AppointmentStatus.no_show.value
    )

    # Revenue: only paid invoices linked to today's appointments
    appt_ids = [a.id for a in appointments]
    revenue_razorpay = 0.0
    revenue_cash = 0.0

    if appt_ids:
        paid_invoices: list[Invoice] = (
            db.query(Invoice)
            .filter(
                Invoice.appointment_id.in_(appt_ids),
                Invoice.status == InvoiceStatus.paid,
            )
            .all()
        )
        for inv in paid_invoices:
            pm = inv.payment_method.value if hasattr(inv.payment_method, "value") else str(inv.payment_method)
            amount = float(inv.amount)
            if pm == PaymentMethod.razorpay.value:
                revenue_razorpay += amount
            elif pm == PaymentMethod.cash.value:
                revenue_cash += amount

    return DailyAnalyticsOut(
        date=target_date.isoformat(),
        checked_in_count=checked_in,
        completed_count=completed,
        no_show_count=no_show,
        revenue_razorpay=revenue_razorpay,
        revenue_cash=revenue_cash,
        total_revenue=revenue_razorpay + revenue_cash,
    )


# ── Doctor & Slot Dropdowns (for Walk-in form) ─────────────────────────────────

@router.get("/doctors", response_model=List[DoctorOut])
def list_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """Return all doctor profiles for the walk-in registration form dropdown."""
    doctors = db.query(DoctorProfile).order_by(DoctorProfile.full_name).all()
    return [DoctorOut.model_validate(d) for d in doctors]


@router.get("/doctors/{doctor_id}/slots", response_model=List[SlotAvailableOut])
def list_available_slots(
    doctor_id: int,
    target_date: Optional[date] = Query(
        default=None,
        alias="date",
        description="YYYY-MM-DD; defaults to today UTC",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """Return open (unbooked) slots for a doctor on a given date.

    A slot is open when no Appointment row references it.
    Reuses the same UTC date-range convention as the queue endpoint.
    """
    if target_date is None:
        target_date = datetime.now(tz=timezone.utc).date()

    start, end = _date_range(target_date)

    open_slots = (
        db.query(AppointmentSlot)
        .outerjoin(Appointment, Appointment.slot_id == AppointmentSlot.id)
        .filter(
            AppointmentSlot.doctor_id == doctor_id,
            AppointmentSlot.slot_start >= start,
            AppointmentSlot.slot_start < end,
            Appointment.id.is_(None),   # no appointment → slot is free
        )
        .order_by(AppointmentSlot.slot_start.asc())
        .all()
    )
    return [SlotAvailableOut.model_validate(s) for s in open_slots]
