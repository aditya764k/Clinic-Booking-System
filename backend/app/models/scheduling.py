"""
Scheduling models: AppointmentSlot
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.identity import DoctorProfile
    from app.models.appointment import Appointment


class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"
    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_start", name="uq_appointment_slots_doctor_slot_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=False)
    slot_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    doctor: Mapped["DoctorProfile"] = relationship("DoctorProfile", back_populates="appointment_slots")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="slot", uselist=False)
