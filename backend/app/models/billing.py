"""
Billing models: Invoice, WebhookEvent
"""
import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import (
    String, DateTime, ForeignKey, Enum as SAEnum, Numeric, JSON, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.identity import User
    from app.models.appointment import Appointment


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class PaymentMethod(str, enum.Enum):
    razorpay = "razorpay"
    cash = "cash"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoicestatus", create_type=True),
        nullable=False,
        default=InvoiceStatus.pending,
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        SAEnum(PaymentMethod, name="paymentmethod", create_type=True),
        nullable=True,
    )
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cash_amount_received: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    receipt_number: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    collected_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="invoice")
    collected_by: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="collected_invoices",
        foreign_keys=[collected_by_user_id],
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    razorpay_event_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    payload_raw: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
