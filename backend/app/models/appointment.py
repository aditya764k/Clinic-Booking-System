"""
Appointment and ClinicalNote models
"""
import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime, ForeignKey, Enum as SAEnum, Text, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.identity import PatientProfile, DoctorProfile
    from app.models.scheduling import AppointmentSlot
    from app.models.billing import Invoice


class AppointmentStatus(str, enum.Enum):
    booked = "booked"
    checked_in = "checked_in"
    in_consultation = "in_consultation"
    completed = "completed"
    billing_pending = "billing_pending"
    paid = "paid"
    cancelled = "cancelled"
    no_show = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=False)
    slot_id: Mapped[int] = mapped_column(ForeignKey("appointment_slots.id"), unique=True, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(AppointmentStatus, name="appointmentstatus", create_type=True),
        nullable=False,
        default=AppointmentStatus.booked,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consultation_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="appointments", foreign_keys=[patient_id])
    doctor: Mapped["DoctorProfile"] = relationship("DoctorProfile", back_populates="appointments", foreign_keys=[doctor_id])
    slot: Mapped["AppointmentSlot"] = relationship("AppointmentSlot", back_populates="appointment")
    clinical_note: Mapped[Optional["ClinicalNote"]] = relationship("ClinicalNote", back_populates="appointment", uselist=False)
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="appointment", uselist=False)


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), unique=True, nullable=False)
    shorthand_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_draft_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_assessment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_suggested_rx: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    finalized_by_doctor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=True)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="clinical_note")
    finalized_by_doctor: Mapped[Optional["DoctorProfile"]] = relationship(
        "DoctorProfile",
        back_populates="finalized_notes",
        foreign_keys=[finalized_by_doctor_id],
    )
