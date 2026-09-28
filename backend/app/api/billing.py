"""
Billing & Payments API endpoints — Module 6.

Endpoints
---------
POST /appointments/{appointment_id}/invoice
    Receptionist creates an invoice for a completed appointment.
    Guard: appointment.status == COMPLETED.
    Transitions appointment → BILLING_PENDING.

POST /invoices/{invoice_id}/razorpay-order
    Receptionist initiates a Razorpay payment order.
    Returns order_id, amount, currency for the frontend Checkout widget.

POST /webhooks/razorpay
    Public endpoint (no auth cookie) — Razorpay calls this after payment capture.
    Security pipeline: HMAC-SHA256 verification → idempotency check →
    amount guard → mutual exclusivity guard → atomic DB update (Invoice + Appointment).

POST /invoices/{invoice_id}/pay-cash
    Receptionist records a cash payment atomically:
    Invoice.status=paid + Appointment → PAID + AuditLog row, all in one transaction.

Design rules
------------
- Pricing is ALWAYS computed server-side (CONSULTATION_FEE constant).
  No endpoint accepts a price from the client payload.
- The webhook uses hmac.compare_digest for constant-time comparison (NFR-SEC-03).
- WebhookEvent unique constraint provides idempotency — a duplicate event_id
  triggers an immediate 200 OK with no state change (Razorpay retry-safe).
- Invoice.payment_method locks payment method — mixing Razorpay and cash paths
  on the same invoice is rejected at the guard level on BOTH sides.
- ALL Invoice + Appointment writes in this module go through a single db.commit()
  call to guarantee atomicity.
- transition_appointment() from Module 4 is the ONLY permitted writer of
  appointments.status. This module respects that constraint.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import razorpay
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.appointment import Appointment, AppointmentStatus
from app.models.audit import AuditLog
from app.models.billing import Invoice, InvoiceStatus, PaymentMethod, WebhookEvent
from app.models.identity import User
from app.schemas.billing import CashPaymentRequest, InvoiceOut, RazorpayOrderOut
from app.services.appointment_state import transition_appointment

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])

# ── Server-side pricing constant ───────────────────────────────────────────────
# Module 6 spec: "use a fixed constant for now."
# DoctorProfile has no consultation_fee column in the current schema.
CONSULTATION_FEE = Decimal("500.00")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _invoice_out(invoice: Invoice) -> InvoiceOut:
    return InvoiceOut(
        id=invoice.id,
        appointment_id=invoice.appointment_id,
        amount=invoice.amount,
        currency=invoice.currency,
        status=invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status),
        payment_method=(
            invoice.payment_method.value
            if invoice.payment_method and hasattr(invoice.payment_method, "value")
            else invoice.payment_method
        ),
        razorpay_order_id=invoice.razorpay_order_id,
        cash_amount_received=invoice.cash_amount_received,
        receipt_number=invoice.receipt_number,
        collected_by_user_id=invoice.collected_by_user_id,
        created_at=invoice.created_at,
        paid_at=invoice.paid_at,
    )


def _get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice: Invoice | None = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice id={invoice_id} not found",
        )
    return invoice


# ── Invoice Creation ───────────────────────────────────────────────────────────

@router.post(
    "/appointments/{appointment_id}/invoice",
    response_model=InvoiceOut,
    status_code=200,
)
def create_invoice(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """FR-REC-04: Receptionist creates an invoice for a completed appointment.

    Guard: appointment must be in COMPLETED status. Transitions to BILLING_PENDING.
    Idempotent: if an invoice already exists for this appointment, returns it immediately.
    Amount is computed server-side from CONSULTATION_FEE — never accepted from client.
    """
    appt: Appointment | None = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment id={appointment_id} not found",
        )

    # Idempotency: return existing invoice if one already exists
    existing: Invoice | None = (
        db.query(Invoice)
        .filter(Invoice.appointment_id == appointment_id)
        .first()
    )
    if existing is not None:
        return _invoice_out(existing)

    # Business guard: appointment must be COMPLETED
    current_status = appt.status.value if hasattr(appt.status, "value") else str(appt.status)
    if current_status != AppointmentStatus.completed.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Invoice can only be created for a completed appointment. "
                f"Current status: '{current_status}'"
            ),
        )

    # Compute amount server-side — client cannot inject pricing
    invoice = Invoice(
        appointment_id=appointment_id,
        amount=CONSULTATION_FEE,
        currency="INR",
        status=InvoiceStatus.pending,
    )
    db.add(invoice)
    db.flush()  # get invoice.id before the transition commit

    # Transition appointment → BILLING_PENDING (single writer rule respected)
    transition_appointment(db, appointment_id, AppointmentStatus.billing_pending, actor=current_user)

    db.refresh(invoice)
    return _invoice_out(invoice)


# ── Razorpay Order Creation ────────────────────────────────────────────────────

@router.post(
    "/invoices/{invoice_id}/razorpay-order",
    response_model=RazorpayOrderOut,
)
def create_razorpay_order(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """FR-BILL-01: Create a Razorpay order for an invoice.

    Mutual exclusivity guard: rejects if invoice is already locked to cash payment.
    Returns order_id + amount (paise) + currency for the frontend Checkout widget.
    """
    invoice = _get_invoice_or_404(db, invoice_id)

    # Guard: already paid
    if invoice.status == InvoiceStatus.paid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice is already paid",
        )

    # Mutual exclusivity guard: cannot create Razorpay order on a cash-locked invoice
    if invoice.payment_method == PaymentMethod.cash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice is locked to cash payment — cannot switch to Razorpay",
        )

    # Create order via Razorpay SDK (Test Mode)
    amount_paise = int(invoice.amount * 100)
    rzp_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
    try:
        order = rzp_client.order.create({
            "amount": amount_paise,
            "currency": invoice.currency,
            "receipt": f"invoice_{invoice.id}",
        })
    except Exception as exc:
        logger.error("Razorpay order creation failed for invoice_id=%s: %s", invoice_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Razorpay order — payment gateway error",
        ) from exc

    invoice.payment_method = PaymentMethod.razorpay
    invoice.razorpay_order_id = order["id"]
    db.commit()

    return RazorpayOrderOut(
        order_id=order["id"],
        amount=amount_paise,
        currency=invoice.currency,
    )


# ── Razorpay Webhook ───────────────────────────────────────────────────────────

@router.post("/webhooks/razorpay", status_code=200)
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str = Header(default=""),
) -> dict:
    """FR-BILL-03 to FR-BILL-06 + NFR-SEC-03: Razorpay payment webhook handler.

    Security + idempotency pipeline (executed in strict order):
    1. HMAC-SHA256 signature verification (constant-time compare_digest).
    2. Idempotency: attempt INSERT into webhook_events — return 200 on duplicate.
    3. Mutual exclusivity: reject if invoice already has cash payment.
    4. Amount guard: reject if paise in webhook != invoice amount.
    5. Atomic DB update: Invoice → paid + Appointment → PAID in one commit.
    """
    # ── 1. HMAC-SHA256 Signature Verification (NFR-SEC-03) ────────────────────
    raw_body: bytes = await request.body()
    secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
    expected_sig = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()

    # compare_digest prevents timing attacks
    if not hmac.compare_digest(expected_sig, x_razorpay_signature):
        logger.warning("Razorpay webhook: invalid signature — rejecting")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    # ── 2. Parse payload ──────────────────────────────────────────────────────
    import json
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed webhook payload — not valid JSON",
        )

    # Only process payment.captured events; silently ack all others
    if payload.get("event") != "payment.captured":
        return {"received": True}

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id: str = payment_entity.get("id", "")
    razorpay_order_id: str = payment_entity.get("order_id", "")
    amount_paise: int = payment_entity.get("amount", 0)

    # Compose a stable event_id: event_type + payment_id
    event_id = f"{payload.get('event', 'unknown')}:{razorpay_payment_id}"

    # ── 3. Idempotency Guard ──────────────────────────────────────────────────
    webhook_event = WebhookEvent(
        razorpay_event_id=event_id,
        payload_raw=payload,
        signature_valid=True,
    )
    db.add(webhook_event)
    try:
        db.flush()
    except IntegrityError:
        # Duplicate event_id — safe no-op. Return 200 so Razorpay stops retrying.
        db.rollback()
        logger.info("Razorpay webhook: duplicate event_id=%s — idempotent skip", event_id)
        return {"received": True}

    # ── 4. Fetch invoice by order_id ──────────────────────────────────────────
    invoice: Invoice | None = (
        db.query(Invoice)
        .filter(Invoice.razorpay_order_id == razorpay_order_id)
        .first()
    )
    if invoice is None:
        db.rollback()
        logger.error("Razorpay webhook: no invoice for order_id=%s", razorpay_order_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No invoice found for Razorpay order_id={razorpay_order_id}",
        )

    # ── 5. Mutual Exclusivity Guard ───────────────────────────────────────────
    if invoice.payment_method == PaymentMethod.cash:
        db.rollback()
        logger.warning(
            "Razorpay webhook: invoice %s is locked to cash — rejecting", invoice.id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is locked to cash payment — Razorpay webhook rejected",
        )

    # ── 6. Amount Guard ───────────────────────────────────────────────────────
    expected_paise = int(invoice.amount * 100)
    if amount_paise != expected_paise:
        db.rollback()
        logger.warning(
            "Razorpay webhook: amount mismatch for invoice %s: got %d paise, expected %d",
            invoice.id,
            amount_paise,
            expected_paise,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Amount mismatch: webhook reported {amount_paise} paise, "
                f"invoice expects {expected_paise} paise"
            ),
        )

    # ── 7. Atomic Update ──────────────────────────────────────────────────────
    # Guard: already paid — skip gracefully (idempotent)
    if invoice.status == InvoiceStatus.paid:
        db.rollback()
        return {"received": True}

    invoice.status = InvoiceStatus.paid
    invoice.razorpay_payment_id = razorpay_payment_id
    invoice.paid_at = datetime.now(tz=timezone.utc)

    # Transition appointment BILLING_PENDING → PAID via the central state machine
    # Note: transition_appointment() calls db.commit() internally.
    # We flush invoice changes first so they're in the same transaction.
    db.flush()
    transition_appointment(
        db, invoice.appointment_id, AppointmentStatus.paid, actor=None  # type: ignore[arg-type]
    )
    # transition_appointment already committed — we're done.

    logger.info(
        "Razorpay webhook: invoice %s and appointment %s marked PAID",
        invoice.id,
        invoice.appointment_id,
    )
    return {"received": True}


# ── Cash Payment ───────────────────────────────────────────────────────────────

@router.post(
    "/invoices/{invoice_id}/pay-cash",
    response_model=InvoiceOut,
)
def pay_cash(
    invoice_id: int,
    body: CashPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("receptionist")),
) -> Any:
    """FR-BILL-08 / FR-BILL-09: Receptionist records a cash payment.

    Guards (in order):
    1. Invoice must not already be paid (409).
    2. Mutual exclusivity: invoice must not be Razorpay-locked (409).
    3. amount_received must be >= invoice.amount (422).

    Atomic update (single db.commit via transition_appointment):
    - Invoice: status=paid, payment_method=cash, cash_amount_received, receipt_number,
               collected_by_user_id, paid_at.
    - Appointment: BILLING_PENDING → PAID via transition_appointment().
    - AuditLog: new row capturing actor, invoice_id, amount_received.
    """
    invoice = _get_invoice_or_404(db, invoice_id)

    # Guard 1: already paid
    if invoice.status == InvoiceStatus.paid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice is already paid",
        )

    # Guard 2: mutual exclusivity — don't touch Razorpay-locked invoices
    if (
        invoice.payment_method == PaymentMethod.razorpay
        and invoice.razorpay_order_id is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invoice is locked to Razorpay payment — cannot record a cash payment. "
                "Please complete the Razorpay transaction or contact support."
            ),
        )

    # Guard 3: amount check
    if Decimal(str(body.amount_received)) < invoice.amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"amount_received ({body.amount_received}) is less than "
                f"invoice amount ({invoice.amount})"
            ),
        )

    # ── Atomic update ─────────────────────────────────────────────────────────
    now = datetime.now(tz=timezone.utc)
    timestamp_ms = int(time.time() * 1000)

    invoice.status = InvoiceStatus.paid
    invoice.payment_method = PaymentMethod.cash
    invoice.cash_amount_received = Decimal(str(body.amount_received))
    invoice.receipt_number = f"RCPT-{invoice.id}-{timestamp_ms}"
    invoice.collected_by_user_id = current_user.id
    invoice.paid_at = now

    # Audit log — encode amount in action string (no extra column needed)
    audit = AuditLog(
        actor_user_id=current_user.id,
        action=f"cash_payment:{body.amount_received}",
        entity_type="invoice",
        entity_id=invoice.id,
        timestamp=now,
    )
    db.add(audit)
    db.flush()  # stage invoice + audit before the transition commit

    # Transition appointment BILLING_PENDING → PAID (single writer rule respected)
    # transition_appointment() calls db.commit() — that commit flushes everything above too.
    transition_appointment(
        db, invoice.appointment_id, AppointmentStatus.paid, actor=current_user
    )

    db.refresh(invoice)
    return _invoice_out(invoice)
