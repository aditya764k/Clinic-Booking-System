"""
Module 6 test suite: Billing & Payments (Razorpay + Cash).

Tests are grouped into:
- Invoice Creation (create, idempotency, wrong-state guard)
- Razorpay Order Creation (success, mutual exclusivity)
- Razorpay Webhook (valid, invalid sig, duplicate replay, amount mismatch, mutual exclusivity)
- Cash Payment (success, already paid, mutual exclusivity)
- RBAC (patient + doctor forbidden on all billing endpoints)

All Razorpay API calls are mocked — no real network calls are made.
HMAC signatures are computed locally using the test webhook secret.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest
from starlette.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.models.appointment import Appointment, AppointmentStatus, ClinicalNote
from app.models.billing import Invoice, InvoiceStatus, PaymentMethod, WebhookEvent
from app.models.identity import DoctorProfile, PatientProfile
from app.models.scheduling import AppointmentSlot
from app.models.audit import AuditLog

# The webhook secret used in conftest.py
WEBHOOK_SECRET = "test_webhook_secret"


# ── Test helpers ───────────────────────────────────────────────────────────────

def _make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute the HMAC-SHA256 signature Razorpay would send."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _razorpay_payload(order_id: str, payment_id: str, amount_paise: int) -> dict:
    """Build a minimal Razorpay payment.captured webhook payload."""
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": amount_paise,
                }
            }
        },
    }


def _register_and_login(client: TestClient, role: str, suffix: str) -> TestClient:
    """Register a user and return the same client (cookies set automatically)."""
    resp = client.post(
        "/auth/register",
        json={
            "email": f"{role}_{suffix}@test.com",
            "password": "Str0ngPass!",
            "role": role,
            "full_name": f"Test {role.capitalize()} {suffix}",
        },
    )
    assert resp.status_code == 201, resp.text
    return client


def _setup_completed_appointment(db_session, receptionist_client: TestClient) -> int:
    """
    Fast-track an appointment to COMPLETED status using direct DB writes.

    We write doctor + patient rows directly to the DB to avoid making extra
    HTTP registration calls that would overwrite the receptionist client's
    auth cookies (each /auth/register call sets a new session cookie).

    Returns appointment_id.
    """
    from app.core.security import hash_password
    from app.models.identity import User, UserRole, DoctorProfile, PatientProfile

    # Create a doctor user + profile directly in the DB
    doc_user = User(
        email=f"dr_setup_{id(db_session)}@test.com",
        hashed_password=hash_password("Str0ngPass!"),
        role=UserRole.doctor,
    )
    db_session.add(doc_user)
    db_session.flush()
    doc_profile = DoctorProfile(user_id=doc_user.id, full_name="Dr Setup")
    db_session.add(doc_profile)

    # Create a patient user + profile directly in the DB
    pat_user = User(
        email=f"pt_setup_{id(db_session)}@test.com",
        hashed_password=hash_password("Str0ngPass!"),
        role=UserRole.patient,
    )
    db_session.add(pat_user)
    db_session.flush()
    pat_profile = PatientProfile(user_id=pat_user.id, full_name="Patient Setup")
    db_session.add(pat_profile)
    db_session.flush()

    # Create a slot
    slot = AppointmentSlot(
        doctor_id=doc_profile.id,
        slot_start=datetime.now(tz=timezone.utc) + timedelta(hours=1),
        slot_end=datetime.now(tz=timezone.utc) + timedelta(hours=2),
    )
    db_session.add(slot)
    db_session.flush()

    # Create a directly-completed appointment
    appt = Appointment(
        patient_id=pat_profile.id,
        doctor_id=doc_profile.id,
        slot_id=slot.id,
        status=AppointmentStatus.completed,
    )
    db_session.add(appt)
    db_session.commit()

    return appt.id



# ── Invoice Creation Tests ─────────────────────────────────────────────────────

def test_create_invoice_success(client, db_session):
    """Receptionist can create an invoice for a completed appointment."""
    rec_client = _register_and_login(client, "receptionist", "inv_create")
    appt_id = _setup_completed_appointment(db_session, rec_client)

    resp = rec_client.post(f"/appointments/{appt_id}/invoice")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["appointment_id"] == appt_id
    assert Decimal(data["amount"]) == Decimal("500.00")
    assert data["status"] == "pending"

    # Appointment should have moved to billing_pending
    db_session.expire_all()
    appt = db_session.get(Appointment, appt_id)
    assert appt.status == AppointmentStatus.billing_pending


def test_create_invoice_idempotent(client, db_session):
    """Creating an invoice twice returns the same invoice — no duplicate."""
    rec_client = _register_and_login(client, "receptionist", "inv_idem")
    appt_id = _setup_completed_appointment(db_session, rec_client)

    resp1 = rec_client.post(f"/appointments/{appt_id}/invoice")
    resp2 = rec_client.post(f"/appointments/{appt_id}/invoice")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]

    # Only one invoice row in the DB
    count = db_session.query(Invoice).filter_by(appointment_id=appt_id).count()
    assert count == 1


def test_create_invoice_wrong_state(client, db_session):
    """Cannot create an invoice for an appointment that is not COMPLETED."""
    rec_client = _register_and_login(client, "receptionist", "inv_wrong")

    # Build a BOOKED appointment directly in DB — no HTTP that would overwrite cookies
    from app.core.security import hash_password
    from app.models.identity import User, UserRole, DoctorProfile, PatientProfile

    doc_user = User(email="dr_ws2@test.com", hashed_password=hash_password("X"), role=UserRole.doctor)
    db_session.add(doc_user)
    db_session.flush()
    dp = DoctorProfile(user_id=doc_user.id, full_name="Dr WS")
    db_session.add(dp)

    pat_user = User(email="pt_ws2@test.com", hashed_password=hash_password("X"), role=UserRole.patient)
    db_session.add(pat_user)
    db_session.flush()
    pp = PatientProfile(user_id=pat_user.id, full_name="Patient WS")
    db_session.add(pp)
    db_session.flush()

    slot = AppointmentSlot(
        doctor_id=dp.id,
        slot_start=datetime.now(tz=timezone.utc) + timedelta(hours=3),
        slot_end=datetime.now(tz=timezone.utc) + timedelta(hours=4),
    )
    db_session.add(slot)
    db_session.flush()

    appt = Appointment(
        patient_id=pp.id, doctor_id=dp.id, slot_id=slot.id,
        status=AppointmentStatus.booked,  # NOT completed
    )
    db_session.add(appt)
    db_session.commit()

    resp = rec_client.post(f"/appointments/{appt.id}/invoice")
    assert resp.status_code == 409



# ── Razorpay Order Tests ───────────────────────────────────────────────────────

def test_razorpay_order_created(client, db_session):
    """Razorpay order endpoint returns order_id and sets payment_method."""
    rec_client = _register_and_login(client, "receptionist", "rzp_order")
    appt_id = _setup_completed_appointment(db_session, rec_client)

    # Create invoice first
    inv_resp = rec_client.post(f"/appointments/{appt_id}/invoice")
    invoice_id = inv_resp.json()["id"]

    mock_order = {"id": "order_test123", "amount": 50000, "currency": "INR"}
    with patch("app.api.billing.razorpay.Client") as MockRzp:
        MockRzp.return_value.order.create.return_value = mock_order
        resp = rec_client.post(f"/invoices/{invoice_id}/razorpay-order")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_id"] == "order_test123"
    assert data["amount"] == 50000

    db_session.expire_all()
    inv = db_session.get(Invoice, invoice_id)
    assert inv.payment_method == PaymentMethod.razorpay
    assert inv.razorpay_order_id == "order_test123"


# ── Razorpay Webhook Tests ─────────────────────────────────────────────────────

def _setup_razorpay_invoice(client, db_session, suffix: str) -> tuple[int, str]:
    """Helper: creates invoice and a Razorpay order. Returns (invoice_id, order_id)."""
    rec_client = _register_and_login(client, "receptionist", suffix)
    appt_id = _setup_completed_appointment(db_session, rec_client)
    inv_resp = rec_client.post(f"/appointments/{appt_id}/invoice")
    invoice_id = inv_resp.json()["id"]

    mock_order = {"id": f"order_{suffix}", "amount": 50000, "currency": "INR"}
    with patch("app.api.billing.razorpay.Client") as MockRzp:
        MockRzp.return_value.order.create.return_value = mock_order
        rec_client.post(f"/invoices/{invoice_id}/razorpay-order")

    return invoice_id, f"order_{suffix}"


def test_razorpay_webhook_valid_signature(client, db_session):
    """Valid webhook atomically marks Invoice and Appointment as PAID."""
    invoice_id, order_id = _setup_razorpay_invoice(client, db_session, "wh_valid")

    payload = _razorpay_payload(order_id, "pay_abc123", 50000)
    body = json.dumps(payload).encode()
    sig = _make_signature(body)

    resp = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
    )
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    inv = db_session.get(Invoice, invoice_id)
    assert inv.status == InvoiceStatus.paid
    assert inv.razorpay_payment_id == "pay_abc123"

    appt = db_session.get(Appointment, inv.appointment_id)
    assert appt.status == AppointmentStatus.paid


def test_razorpay_webhook_invalid_signature(client, db_session):
    """Webhook with bad signature is rejected 400, state unchanged."""
    invoice_id, order_id = _setup_razorpay_invoice(client, db_session, "wh_badsig")

    payload = _razorpay_payload(order_id, "pay_bad", 50000)
    body = json.dumps(payload).encode()

    resp = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid_sig"},
    )
    assert resp.status_code == 400

    # State must be unchanged
    db_session.expire_all()
    inv = db_session.get(Invoice, invoice_id)
    assert inv.status == InvoiceStatus.pending


def test_razorpay_webhook_duplicate_replay(client, db_session):
    """Duplicate webhook event returns 200 OK but is a no-op (idempotent)."""
    invoice_id, order_id = _setup_razorpay_invoice(client, db_session, "wh_dup")

    payload = _razorpay_payload(order_id, "pay_dup123", 50000)
    body = json.dumps(payload).encode()
    sig = _make_signature(body)
    headers = {"Content-Type": "application/json", "X-Razorpay-Signature": sig}

    # First call — should succeed
    resp1 = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert resp1.status_code == 200

    # Second call — same signature + payload — must be idempotent 200, NOT an error
    resp2 = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert resp2.status_code == 200

    # Exactly one WebhookEvent row
    db_session.expire_all()
    count = db_session.query(WebhookEvent).count()
    assert count == 1


def test_razorpay_webhook_amount_mismatch(client, db_session):
    """Webhook with wrong paise amount is rejected, state unchanged."""
    invoice_id, order_id = _setup_razorpay_invoice(client, db_session, "wh_amt")

    # Send 1 paise instead of 50000
    payload = _razorpay_payload(order_id, "pay_wrong", 1)
    body = json.dumps(payload).encode()
    sig = _make_signature(body)

    resp = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
    )
    assert resp.status_code == 400

    db_session.expire_all()
    inv = db_session.get(Invoice, invoice_id)
    assert inv.status == InvoiceStatus.pending


# ── Cash Payment Tests ─────────────────────────────────────────────────────────

def test_cash_confirmation_success(client, db_session):
    """Cash payment atomically marks Invoice PAID, Appointment PAID, AuditLog written."""
    rec_client = _register_and_login(client, "receptionist", "cash_ok")
    appt_id = _setup_completed_appointment(db_session, rec_client)
    inv_resp = rec_client.post(f"/appointments/{appt_id}/invoice")
    invoice_id = inv_resp.json()["id"]

    resp = rec_client.post(
        f"/invoices/{invoice_id}/pay-cash",
        json={"amount_received": 500.00},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "paid"
    assert data["payment_method"] == "cash"
    assert data["receipt_number"] is not None

    db_session.expire_all()
    inv = db_session.get(Invoice, invoice_id)
    assert inv.status == InvoiceStatus.paid
    assert inv.payment_method == PaymentMethod.cash

    appt = db_session.get(Appointment, appt_id)
    assert appt.status == AppointmentStatus.paid

    # AuditLog row must exist
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == invoice_id, AuditLog.entity_type == "invoice")
        .first()
    )
    assert audit is not None
    assert "cash_payment" in audit.action
    assert "500" in audit.action


def test_cash_confirmation_already_paid(client, db_session):
    """Paying cash on an already-paid invoice returns 409."""
    rec_client = _register_and_login(client, "receptionist", "cash_dup")
    appt_id = _setup_completed_appointment(db_session, rec_client)
    inv_resp = rec_client.post(f"/appointments/{appt_id}/invoice")
    invoice_id = inv_resp.json()["id"]

    rec_client.post(f"/invoices/{invoice_id}/pay-cash", json={"amount_received": 500.00})
    # Second attempt
    resp = rec_client.post(f"/invoices/{invoice_id}/pay-cash", json={"amount_received": 500.00})
    assert resp.status_code == 409


def test_cash_insufficient_amount(client, db_session):
    """Paying less than invoice amount returns 422."""
    rec_client = _register_and_login(client, "receptionist", "cash_insuf")
    appt_id = _setup_completed_appointment(db_session, rec_client)
    inv_resp = rec_client.post(f"/appointments/{appt_id}/invoice")
    invoice_id = inv_resp.json()["id"]

    resp = rec_client.post(
        f"/invoices/{invoice_id}/pay-cash",
        json={"amount_received": 100.00},  # Less than ₹500
    )
    assert resp.status_code == 422


# ── Mutual Exclusivity Tests ───────────────────────────────────────────────────

def test_mutual_exclusivity_cash_on_razorpay_invoice(client, db_session):
    """Cannot pay cash on an invoice already locked to Razorpay."""
    invoice_id, _ = _setup_razorpay_invoice(client, db_session, "mutex_rzp")

    # Use same receptionist client (already logged in via setup helper)
    # We need the receptionist's client — register another one
    rec_client = _register_and_login(client, "receptionist", "mutex_rzp_rec")

    resp = rec_client.post(
        f"/invoices/{invoice_id}/pay-cash",
        json={"amount_received": 500.00},
    )
    assert resp.status_code == 409
    assert "Razorpay" in resp.json()["detail"]


def test_mutual_exclusivity_razorpay_webhook_on_cash_invoice(client, db_session):
    """Razorpay webhook is rejected if invoice is already cash-paid."""
    rec_client = _register_and_login(client, "receptionist", "mutex_cash")
    appt_id = _setup_completed_appointment(db_session, rec_client)
    inv_resp = rec_client.post(f"/appointments/{appt_id}/invoice")
    invoice_id = inv_resp.json()["id"]

    # Pay via cash first
    rec_client.post(f"/invoices/{invoice_id}/pay-cash", json={"amount_received": 500.00})

    # Now send a Razorpay webhook for the same invoice
    db_session.expire_all()
    inv = db_session.get(Invoice, invoice_id)

    # Manually set a fake order_id to simulate what webhook would reference
    inv.razorpay_order_id = "order_fake_mutex"
    db_session.commit()

    payload = _razorpay_payload("order_fake_mutex", "pay_mutex", 50000)
    body = json.dumps(payload).encode()
    sig = _make_signature(body)

    resp = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
    )
    assert resp.status_code == 400
    assert "cash" in resp.json()["detail"].lower()


# ── RBAC Tests ─────────────────────────────────────────────────────────────────

def test_rbac_patient_forbidden(client, db_session):
    """Patient cannot access any billing endpoint."""
    patient_client = _register_and_login(client, "patient", "rbac_pat")

    assert patient_client.post("/appointments/1/invoice").status_code == 403
    assert patient_client.post("/invoices/1/razorpay-order").status_code == 403
    assert patient_client.post(
        "/invoices/1/pay-cash", json={"amount_received": 500}
    ).status_code == 403


def test_rbac_doctor_forbidden(client, db_session):
    """Doctor cannot access any billing endpoint."""
    doctor_client = _register_and_login(client, "doctor", "rbac_doc")

    assert doctor_client.post("/appointments/1/invoice").status_code == 403
    assert doctor_client.post("/invoices/1/razorpay-order").status_code == 403
    assert doctor_client.post(
        "/invoices/1/pay-cash", json={"amount_received": 500}
    ).status_code == 403
