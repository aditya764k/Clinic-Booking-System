"""
Pydantic schemas for Module 7: Receptionist Operations & Analytics.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class WalkInRegistrationRequest(BaseModel):
    """Request body for POST /receptionist/walk-in.

    ``email`` is optional for true walk-ins who have no email address.
    When omitted the backend auto-generates a placeholder address in the form
    ``walkin_{phone}@clinic.internal`` to satisfy the User.email UNIQUE
    constraint without requiring real contact data.

    ``phone`` is required and acts as the primary deduplication key for
    patients who don't have an email address yet exist in the system.
    """

    first_name: str
    last_name: str
    phone: str
    email: str
    doctor_id: int   # DoctorProfile.id (NOT User.id)
    slot_id: int     # AppointmentSlot.id

    @field_validator("phone")
    @classmethod
    def phone_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("phone must not be empty")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name fields must not be empty")
        return v


class WalkInOut(BaseModel):
    """Response returned after a successful walk-in registration."""

    appointment_id: int
    patient_id: int        # PatientProfile.id
    patient_name: str
    status: str            # appointment status
    slot_start: datetime
    slot_end: datetime
    is_new_patient: bool   # True if a new User + PatientProfile were created
    invoice_id: int
    amount: float
    currency: str


class DoctorOut(BaseModel):
    """A doctor row for the walk-in form's doctor dropdown."""

    id: int          # DoctorProfile.id
    full_name: str
    specialization: Optional[str] = None

    model_config = {"from_attributes": True}


class SlotAvailableOut(BaseModel):
    """An open appointment slot for the walk-in form's slot dropdown."""

    id: int
    slot_start: datetime
    slot_end: datetime

    model_config = {"from_attributes": True}


class DailyAnalyticsOut(BaseModel):
    """Aggregated daily operational metrics for the receptionist dashboard.

    Revenue figures reflect only paid invoices whose linked appointment slot
    falls on the requested date. Pending/failed invoices are excluded.
    """

    date: str                    # ISO date string e.g. "2026-09-29"
    checked_in_count: int
    completed_count: int
    no_show_count: int
    revenue_razorpay: float
    revenue_cash: float
    total_revenue: float
