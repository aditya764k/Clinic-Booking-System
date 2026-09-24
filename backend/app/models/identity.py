"""
Identity models: User, PatientProfile, DoctorProfile
"""
import enum
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    String, Enum as SAEnum, DateTime, Date, JSON, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.billing import Invoice
    from app.models.appointment import Appointment, ClinicalNote
    from app.models.scheduling import AppointmentSlot

class UserRole(str, enum.Enum):
    patient = "patient"
    receptionist = "receptionist"
    doctor = "doctor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    google_sub: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", create_type=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    patient_profile: Mapped[Optional["PatientProfile"]] = relationship("PatientProfile", back_populates="user", uselist=False)
    doctor_profile: Mapped[Optional["DoctorProfile"]] = relationship("DoctorProfile", back_populates="user", uselist=False)
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="actor", foreign_keys="[AuditLog.actor_user_id]")
    collected_invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="collected_by", foreign_keys="[Invoice.collected_by_user_id]")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="patient_profile")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="patient", foreign_keys="[Appointment.patient_id]")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    working_hours_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="doctor_profile")
    appointment_slots: Mapped[List["AppointmentSlot"]] = relationship("AppointmentSlot", back_populates="doctor")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="doctor", foreign_keys="[Appointment.doctor_id]")
    finalized_notes: Mapped[List["ClinicalNote"]] = relationship("ClinicalNote", back_populates="finalized_by_doctor", foreign_keys="[ClinicalNote.finalized_by_doctor_id]")
