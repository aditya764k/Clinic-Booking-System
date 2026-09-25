"""
Pydantic schemas for Module 3: Scheduling & Availability.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

# Valid weekday keys for working_hours_config
WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class DaySchedule(BaseModel):
    """Working hours for a single weekday."""

    start: str  # "HH:MM"
    end: str  # "HH:MM"

    @field_validator("start", "end")
    @classmethod
    def valid_time_format(cls, v: str) -> str:
        if not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM format")
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Time out of range")
        return v

    @model_validator(mode="after")
    def start_before_end(self) -> "DaySchedule":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class WorkingHoursConfig(BaseModel):
    """Full working-hours configuration stored on DoctorProfile."""

    slot_duration_minutes: int
    schedule: dict[str, Optional[DaySchedule]]

    @field_validator("slot_duration_minutes")
    @classmethod
    def valid_duration(cls, v: int) -> int:
        if not (5 <= v <= 240):
            raise ValueError("slot_duration_minutes must be between 5 and 240")
        return v

    @field_validator("schedule")
    @classmethod
    def valid_schedule_keys(cls, v: dict) -> dict:
        invalid = set(v.keys()) - WEEKDAYS
        if invalid:
            raise ValueError(f"Invalid schedule keys: {invalid}. Must be weekday names.")
        return v


class SlotOut(BaseModel):
    """A single appointment slot returned by the availability endpoint."""

    id: int
    slot_start: datetime
    slot_end: datetime

    model_config = {"from_attributes": True}


class BookingRequest(BaseModel):
    """Request body for POST /appointments/book."""

    slot_id: int


class AppointmentOut(BaseModel):
    """Response returned after a successful booking or state transition."""

    id: int
    status: str
    slot_start: datetime
    slot_end: datetime
    doctor_name: str
    patient_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AppointmentQueueItem(BaseModel):
    """A single row in the receptionist/doctor queue response."""

    id: int
    status: str
    patient_name: str
    doctor_name: str
    slot_start: datetime
    slot_end: datetime

    model_config = {"from_attributes": True}
