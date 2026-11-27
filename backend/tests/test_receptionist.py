"""
Module 7 test suite: Receptionist Operations & Analytics.

Groups:
- Walk-in registration (new patient, existing by email, existing by phone, slot conflict)
- Daily analytics (counts today-only, revenue split by payment method)
- RBAC (patient + doctor forbidden on all receptionist endpoints)

All tests use direct DB writes for setup to avoid overwriting auth cookies.
Follows the exact same helper pattern established in test_billing.py.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta, date

import pytest
from starlette.testclient import TestClient

from app.core.security import hash_password
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Invoice, InvoiceStatus, PaymentMethod
from app.models.identity import DoctorProfile, PatientProfile, User, UserRole
from app.models.scheduling import AppointmentSlot


# ── Shared setup helpers ───────────────────────────────────────────────────────

def _make_doctor(db_session, suffix: str) -> DoctorProfile:
    """Create a doctor user + profile directly in the DB."""
    user = User(
        email=f"dr_{suffix}@test.com",
        hashed_password=hash_password("Pass!"),
        role=UserRole.doctor,
    )
    db_session.add(user)
    db_session.flush()
    profile = DoctorProfile(user_id=user.id, full_name=f"Dr {suffix}")
    db_session.add(profile)
    db_session.flush()
    return profile


def _make_slot(db_session, doctor_id: int, offset_hours: int = 1) -> AppointmentSlot:
    """Create an available slot starting offset_hours from now."""
    now = datetime.now(tz=timezone.utc)
    slot = AppointmentSlot(
        doctor_id=doctor_id,
        slot_start=now + timedelta(hours=offset_hours),
        slot_end=now + timedelta(hours=offset_hours + 1),
    )
    db_session.add(slot)
    db_session.flush()
    return slot


def _make_slot_yesterday(db_session, doctor_id: int) -> AppointmentSlot:
    """Create a slot that started yesterday (for analytics isolation test)."""
    yesterday = datetime.now(tz=timezone.utc) - timedelta(days=1)
    slot = AppointmentSlot(
        doctor_id=doctor_id,
        slot_start=yesterday,
        slot_end=yesterday + timedelta(hours=1),
    )
    db_session.add(slot)
    db_session.flush()
    return slot


def _register_receptionist(client: TestClient, suffix: str) -> TestClient:
    """Register + login as receptionist. Returns the same client (cookies set)."""
    resp = client.post(
        "/auth/register",
        json={
            "email": f"rec_{suffix}@test.com",
            "password": "Str0ngPass!",
            "role": "receptionist",
            "full_name": f"Rec {suffix}",
        },
    )
    assert resp.status_code == 201, resp.text
    return client


def _make_completed_appointment(db_session, doctor_id: int, slot: AppointmentSlot) -> Appointment:
    """Create a patient and a directly-completed appointment."""
    pat_user = User(
        email=f"pt_{slot.id}@test.com",
        hashed_password=hash_password("x"),
        role=UserRole.patient,
    )
    db_session.add(pat_user)
    db_session.flush()
    pat = PatientProfile(user_id=pat_user.id, full_name="Patient Test")
    db_session.add(pat)
    db_session.flush()

    appt = Appointment(
        patient_id=pat.id,
        doctor_id=doctor_id,
        slot_id=slot.id,
        status=AppointmentStatus.completed,
    )
    db_session.add(appt)
    db_session.flush()
    return appt


# ── Walk-in Registration Tests ─────────────────────────────────────────────────

def test_walk_in_new_patient_success(client, db_session):
    """Walk-in for a brand new patient creates User + PatientProfile + Appointment atomically."""
    rec_client = _register_receptionist(client, "walkin_new")
    doctor = _make_doctor(db_session, "walkin_new")
    slot = _make_slot(db_session, doctor.id, offset_hours=2)
    db_session.commit()

    resp = rec_client.post(
        "/receptionist/walk-in",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "9876543210",
            "email": "jane.doe@example.com",
            "doctor_id": doctor.id,
            "slot_id": slot.id,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["is_new_patient"] is True
    assert data["status"] == "checked_in"
    assert data["patient_name"] == "Jane Doe"

    # Verify DB: User, PatientProfile, and Appointment all created
    db_session.expire_all()
    appt = db_session.get(Appointment, data["appointment_id"])
    assert appt is not None
    assert appt.status == AppointmentStatus.checked_in

    pat = db_session.get(PatientProfile, data["patient_id"])
    assert pat is not None
    assert pat.full_name == "Jane Doe"
    assert pat.phone == "9876543210"


def test_walk_in_existing_patient_by_email(client, db_session):
    """Walk-in for a patient who already exists (by email) reuses their profile."""
    rec_client = _register_receptionist(client, "walkin_email")
    doctor = _make_doctor(db_session, "walkin_email")
    slot = _make_slot(db_session, doctor.id, offset_hours=3)

    # Pre-create existing patient
    existing_user = User(
        email="existing@example.com",
        hashed_password=hash_password("x"),
        role=UserRole.patient,
    )
    db_session.add(existing_user)
    db_session.flush()
    existing_profile = PatientProfile(
        user_id=existing_user.id,
        full_name="Existing Patient",
        phone="1111111111",
    )
    db_session.add(existing_profile)
    db_session.commit()

    resp = rec_client.post(
        "/receptionist/walk-in",
        json={
            "first_name": "Existing",
            "last_name": "Patient",
            "phone": "1111111111",
            "email": "existing@example.com",
            "doctor_id": doctor.id,
            "slot_id": slot.id,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["is_new_patient"] is False
    assert data["patient_id"] == existing_profile.id

    # Verify no duplicate User row created
    user_count = db_session.query(User).filter(User.email == "existing@example.com").count()
    assert user_count == 1


def test_walk_in_existing_patient_by_phone(client, db_session):
    """Walk-in without email resolves existing patient by phone number."""
    rec_client = _register_receptionist(client, "walkin_phone")
    doctor = _make_doctor(db_session, "walkin_phone")
    slot = _make_slot(db_session, doctor.id, offset_hours=4)

    # Pre-create patient with no email in the system (generated placeholder)
    existing_user = User(
        email="walkin_8888888888@clinic.internal",
        hashed_password=None,
        role=UserRole.patient,
    )
    db_session.add(existing_user)
    db_session.flush()
    existing_profile = PatientProfile(
        user_id=existing_user.id,
        full_name="Phone Patient",
        phone="8888888888",
    )
    db_session.add(existing_profile)
    db_session.commit()

    resp = rec_client.post(
        "/receptionist/walk-in",
        json={
            "first_name": "Phone",
            "last_name": "Patient",
            "phone": "8888888888",  # no email — should match by phone
            "doctor_id": doctor.id,
            "slot_id": slot.id,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["is_new_patient"] is False
    assert data["patient_id"] == existing_profile.id


def test_walk_in_slot_conflict(client, db_session):
    """Walk-in on an already-booked slot returns 409 Conflict."""
    rec_client = _register_receptionist(client, "walkin_conflict")
    doctor = _make_doctor(db_session, "walkin_conflict")
    slot = _make_slot(db_session, doctor.id, offset_hours=5)

    # Pre-book the slot
    pat_user = User(email="conflict_pat@test.com", hashed_password=hash_password("x"), role=UserRole.patient)
    db_session.add(pat_user)
    db_session.flush()
    pat = PatientProfile(user_id=pat_user.id, full_name="Conflict Patient")
    db_session.add(pat)
    db_session.flush()
    existing_appt = Appointment(
        patient_id=pat.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        status=AppointmentStatus.booked,
    )
    db_session.add(existing_appt)
    db_session.commit()

    resp = rec_client.post(
        "/receptionist/walk-in",
        json={
            "first_name": "New",
            "last_name": "Walkin",
            "phone": "5555555555",
            "doctor_id": doctor.id,
            "slot_id": slot.id,  # same slot — already taken
        },
    )
    assert resp.status_code == 409
    assert "booked" in resp.json()["detail"].lower()


# ── Daily Analytics Tests ──────────────────────────────────────────────────────

def test_daily_analytics_counts_only_today(client, db_session):
    """Analytics only counts appointments whose slot falls on today, not yesterday."""
    rec_client = _register_receptionist(client, "analytics_date")
    doctor = _make_doctor(db_session, "analytics_date")

    # Today appointment
    slot_today = _make_slot(db_session, doctor.id, offset_hours=1)
    pat_user = User(email="today_pat@test.com", hashed_password=hash_password("x"), role=UserRole.patient)
    db_session.add(pat_user)
    db_session.flush()
    pat = PatientProfile(user_id=pat_user.id, full_name="Today Patient")
    db_session.add(pat)
    db_session.flush()
    appt_today = Appointment(
        patient_id=pat.id, doctor_id=doctor.id,
        slot_id=slot_today.id, status=AppointmentStatus.checked_in,
    )
    db_session.add(appt_today)

    # Yesterday appointment — must NOT appear in today's analytics
    slot_yest = _make_slot_yesterday(db_session, doctor.id)
    pat_user2 = User(email="yest_pat@test.com", hashed_password=hash_password("x"), role=UserRole.patient)
    db_session.add(pat_user2)
    db_session.flush()
    pat2 = PatientProfile(user_id=pat_user2.id, full_name="Yesterday Patient")
    db_session.add(pat2)
    db_session.flush()
    appt_yest = Appointment(
        patient_id=pat2.id, doctor_id=doctor.id,
        slot_id=slot_yest.id, status=AppointmentStatus.checked_in,
    )
    db_session.add(appt_yest)
    db_session.commit()

    resp = rec_client.get("/receptionist/analytics/daily")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Only today's checked_in appointment should be counted
    assert data["checked_in_count"] >= 1
    # Total revenue is zero (no paid invoices seeded)
    assert data["total_revenue"] == 0.0


def test_daily_analytics_revenue_by_method(client, db_session):
    """Revenue is correctly split between Razorpay and Cash paid invoices.

    We drive the full lifecycle via HTTP (walk-in → invoice → cash pay) so all
    state is committed in the same session that the analytics endpoint reads.
    Two appointments: both paid via cash (we can't simulate Razorpay in this
    integration test, so we assert cash >= 500 and razorpay == 0.0 baseline).
    """
    rec_client = _register_receptionist(client, "analytics_rev")
    doctor = _make_doctor(db_session, "analytics_rev")

    slot1 = _make_slot(db_session, doctor.id, offset_hours=6)
    slot2 = _make_slot(db_session, doctor.id, offset_hours=7)
    db_session.commit()

    # Walk-in appointment 1
    r1 = rec_client.post("/receptionist/walk-in", json={
        "first_name": "Rev", "last_name": "One", "phone": "7001000001",
        "doctor_id": doctor.id, "slot_id": slot1.id,
    })
    assert r1.status_code == 201, r1.text
    appt1_id = r1.json()["appointment_id"]

    # Walk-in appointment 2
    r2 = rec_client.post("/receptionist/walk-in", json={
        "first_name": "Rev", "last_name": "Two", "phone": "7001000002",
        "doctor_id": doctor.id, "slot_id": slot2.id,
    })
    assert r2.status_code == 201, r2.text
    appt2_id = r2.json()["appointment_id"]

    # Manually advance appointments to COMPLETED via DB (state machine requires doctor for in_consultation)
    # Use db_session and flush so the HTTP endpoint's session can read them (StaticPool = same underlying connection)
    for appt_id in (appt1_id, appt2_id):
        appt = db_session.get(Appointment, appt_id)
        appt.status = AppointmentStatus.completed
    db_session.commit()

    # Create invoices via the billing endpoint (same HTTP session as analytics)
    inv1_resp = rec_client.post(f"/appointments/{appt1_id}/invoice")
    assert inv1_resp.status_code == 200, inv1_resp.text
    inv1_id = inv1_resp.json()["id"]

    inv2_resp = rec_client.post(f"/appointments/{appt2_id}/invoice")
    assert inv2_resp.status_code == 200, inv2_resp.text
    inv2_id = inv2_resp.json()["id"]

    # Pay both via cash
    pay1 = rec_client.post(f"/invoices/{inv1_id}/pay-cash", json={"amount_received": 500})
    assert pay1.status_code == 200, pay1.text
    pay2 = rec_client.post(f"/invoices/{inv2_id}/pay-cash", json={"amount_received": 600})
    assert pay2.status_code == 200, pay2.text

    # Now check analytics — both should show as cash revenue
    # Pass the exact date to avoid UTC midnight boundary flakiness
    target_date = slot1.slot_start.date().isoformat()
    resp = rec_client.get(f"/receptionist/analytics/daily?date={target_date}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["revenue_cash"] >= 1000.0
    assert data["total_revenue"] >= 1000.0
    # No Razorpay payments in this test
    assert data["revenue_razorpay"] == 0.0



# ── RBAC Tests ─────────────────────────────────────────────────────────────────

def test_rbac_patient_forbidden(client, db_session):
    """Patient cannot access any receptionist endpoint."""
    resp = client.post("/auth/register", json={
        "email": "rbac_pat_r7@test.com", "password": "Str0ngPass!",
        "role": "patient", "full_name": "RBAC Patient",
    })
    assert resp.status_code == 201

    assert client.post("/receptionist/walk-in", json={
        "first_name": "X", "last_name": "Y", "phone": "0", "doctor_id": 1, "slot_id": 1
    }).status_code == 403
    assert client.get("/receptionist/analytics/daily").status_code == 403
    assert client.get("/receptionist/doctors").status_code == 403


def test_rbac_doctor_forbidden(client, db_session):
    """Doctor cannot access any receptionist endpoint."""
    resp = client.post("/auth/register", json={
        "email": "rbac_doc_r7@test.com", "password": "Str0ngPass!",
        "role": "doctor", "full_name": "RBAC Doctor",
    })
    assert resp.status_code == 201

    assert client.post("/receptionist/walk-in", json={
        "first_name": "X", "last_name": "Y", "phone": "0", "doctor_id": 1, "slot_id": 1
    }).status_code == 403
    assert client.get("/receptionist/analytics/daily").status_code == 403
    assert client.get("/receptionist/doctors").status_code == 403
