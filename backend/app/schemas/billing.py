"""
Pydantic schemas for Module 6: Billing & Payments (Razorpay + Cash).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class InvoiceOut(BaseModel):
    """Full invoice row shape returned by billing endpoints."""

    id: int
    appointment_id: int
    amount: Decimal
    currency: str
    status: str
    payment_method: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    cash_amount_received: Optional[Decimal] = None
    receipt_number: Optional[str] = None
    collected_by_user_id: Optional[int] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RazorpayOrderOut(BaseModel):
    """Returned after creating a Razorpay order, consumed by the frontend checkout widget."""

    order_id: str
    amount: int    # in paise (100 paise = ₹1)
    currency: str


class CashPaymentRequest(BaseModel):
    """Request body for POST /invoices/{id}/pay-cash.

    Only captures the amount tendered by the patient.
    All pricing logic lives server-side — the client never dictates the invoice amount.
    """

    amount_received: float

    @field_validator("amount_received")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount_received must be a positive number")
        return v
