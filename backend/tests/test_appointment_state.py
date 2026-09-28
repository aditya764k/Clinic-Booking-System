"""
Integration tests for Module 4: Appointment State Machine.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import status
from starlette.testclient import TestClient

from app.models.appointment import Appointment, AppointmentStatus
from app.models.scheduling import AppointmentSlot
from app.services.appointment_state import LEGAL_TRANSITIONS, transition_appointment
from app.core.exceptions import IllegalTransitionError


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_user(client: TestClient, role: str, suffix: str) -> int | None:
    """Register a user; return profile_id (None for receptionist — no profile table)."""
    resp = client.post(
        "/auth/register",
        json={"email": f"{suffix}@t.com", "password": "Str0ngPass!",
              "role": role, "full_name": f"{role} {suffix}"},
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json().get("profile_id")
    if role != "receptionist":
        assert pid is not None, f"profile_id missing: {resp.json()}"
    return pid


def login(client: TestClient, suffix: str) -> None:
    """Log in as an already-registered user (rotates the shared cookie jar)."""
    client.post("/auth/login",
                json={"email": f"{suffix}@t.com", "password": "Str0ngPass!"})


def _seed(db, doctor_id: int, patient_id: int,
          s: AppointmentStatus, d: date | None = None) -> Appointment:
    if d is None:
        d = datetime.now(tz=timezone.utc).date()
    start = datetime(d.year, d.month, d.day, 9, 0, tzinfo=timezone.utc)
    slot = AppointmentSlot(doctor_id=doctor_id, slot_start=start,
                           slot_end=start + timedelta(hours=1))
    db.add(slot); db.flush()
    appt = Appointment(patient_id=patient_id, doctor_id=doctor_id,
                       slot_id=slot.id, status=s)
    db.add(appt); db.commit(); db.refresh(appt)
    return appt


# ══════════════════════════════════════════════════════════════════════════════
# TestLegalTransitions
# ══════════════════════════════════════════════════════════════════════════════

ALL_STATUSES = list(AppointmentStatus)

LEGAL_PAIRS = [(f, t) for f, ts in LEGAL_TRANSITIONS.items() for t in ts]
ILLEGAL_PAIRS = [
    (f, t) for f in ALL_STATUSES for t in ALL_STATUSES
    if t not in LEGAL_TRANSITIONS.get(f, set())
]


class TestLegalTransitions:
    @pytest.mark.parametrize("from_status,to_status", LEGAL_PAIRS)
    def test_service_level_transition(self, from_status, to_status, client, db_session):
        from app.models.identity import User, UserRole, DoctorProfile, PatientProfile
        from app.core.security import hash_password

        u_doc = User(email=f"d_{from_status.value}_{to_status.value}@t.com",
                     hashed_password=hash_password("P1!"), role=UserRole.doctor)
        db_session.add(u_doc); db_session.flush()
        doc = DoctorProfile(user_id=u_doc.id, full_name="Doc")
        db_session.add(doc)

        u_pat = User(email=f"p_{from_status.value}_{to_status.value}@t.com",
                     hashed_password=hash_password("P1!"), role=UserRole.patient)
        db_session.add(u_pat); db_session.flush()
        pat = PatientProfile(user_id=u_pat.id, full_name="Pat")
        db_session.add(pat); db_session.flush()

        appt = _seed(db_session, doc.id, pat.id, from_status)
        updated = transition_appointment(db_session, appt.id, to_status, actor=u_doc)

        assert updated.status == to_status
        if to_status == AppointmentStatus.checked_in:
            assert updated.checked_in_at is not None
        elif to_status == AppointmentStatus.in_consultation:
            assert updated.consultation_started_at is not None
        elif to_status == AppointmentStatus.completed:
            assert updated.completed_at is not None


# ══════════════════════════════════════════════════════════════════════════════
# TestIllegalTransitions
# ══════════════════════════════════════════════════════════════════════════════

class TestIllegalTransitions:
    @pytest.mark.parametrize("from_status,to_status", ILLEGAL_PAIRS)
    def test_service_raises_illegal_transition(self, from_status, to_status, client, db_session):
        from app.models.identity import User, UserRole, DoctorProfile, PatientProfile
        from app.core.security import hash_password

        uid = f"{from_status.value[:3]}_{to_status.value[:3]}"
        u_doc = User(email=f"id_{uid}@t.com",
                     hashed_password=hash_password("P1!"), role=UserRole.doctor)
        db_session.add(u_doc); db_session.flush()
        doc = DoctorProfile(user_id=u_doc.id, full_name="Doc")
        db_session.add(doc)

        u_pat = User(email=f"ip_{uid}@t.com",
                     hashed_password=hash_password("P1!"), role=UserRole.patient)
        db_session.add(u_pat); db_session.flush()
        from app.models.identity import PatientProfile as _PP
        pat = _PP(user_id=u_pat.id, full_name="Pat")
        db_session.add(pat); db_session.flush()

        appt = _seed(db_session, doc.id, pat.id, from_status)
        with pytest.raises(IllegalTransitionError) as ei:
            transition_appointment(db_session, appt.id, to_status, actor=u_doc)

        assert ei.value.current_status == from_status
        assert ei.value.attempted_status == to_status
        assert str(appt.id) in str(ei.value)


# ══════════════════════════════════════════════════════════════════════════════
# TestRBAC
# ══════════════════════════════════════════════════════════════════════════════

class TestRBAC:
    def _setup(self, client, db_session):
        doc_pid = register_user(client, "doctor", "rbac_doc")
        pat_pid = register_user(client, "patient", "rbac_pat")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked)
        return appt

    def test_patient_cannot_check_in(self, client, db_session):
        appt = self._setup(client, db_session)
        login(client, "rbac_pat")
        r = client.post(f"/appointments/{appt.id}/check-in")
        assert r.status_code == 403

    def test_doctor_cannot_check_in(self, client, db_session):
        appt = self._setup(client, db_session)
        login(client, "rbac_doc")
        r = client.post(f"/appointments/{appt.id}/check-in")
        assert r.status_code == 403

    def test_patient_cannot_start_consultation(self, client, db_session):
        appt = self._setup(client, db_session)
        login(client, "rbac_pat")
        r = client.post(f"/appointments/{appt.id}/start-consultation")
        assert r.status_code == 403

    def test_receptionist_cannot_start_consultation(self, client, db_session):
        appt = self._setup(client, db_session)
        register_user(client, "receptionist", "rbac_rec")
        r = client.post(f"/appointments/{appt.id}/start-consultation")
        assert r.status_code == 403

    def test_doctor_cannot_cancel(self, client, db_session):
        appt = self._setup(client, db_session)
        login(client, "rbac_doc")
        r = client.post(f"/appointments/{appt.id}/cancel")
        assert r.status_code == 403

    def test_unauthenticated_cannot_check_in(self, client, db_session):
        appt = self._setup(client, db_session)
        client.cookies.clear()
        r = client.post(f"/appointments/{appt.id}/check-in")
        assert r.status_code == 401

    def test_doctor_cannot_view_receptionist_queue(self, client):
        register_user(client, "doctor", "rbac_qd")
        r = client.get("/appointments/queue/today")
        assert r.status_code == 403

    def test_patient_cannot_view_receptionist_queue(self, client):
        register_user(client, "patient", "rbac_qp")
        r = client.get("/appointments/queue/today")
        assert r.status_code == 403

    def test_receptionist_cannot_view_doctor_queue(self, client):
        register_user(client, "receptionist", "rbac_qr")
        r = client.get("/appointments/queue/mine")
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# TestOwnership
# ══════════════════════════════════════════════════════════════════════════════

class TestOwnership:
    def test_wrong_doctor_cannot_start_consultation(self, client, db_session):
        doc1_pid = register_user(client, "doctor", "own_doc1")
        pat_pid   = register_user(client, "patient", "own_pat1")
        appt = _seed(db_session, doc1_pid, pat_pid, AppointmentStatus.checked_in)
        # Register doc2; their cookies are now active on the shared client
        register_user(client, "doctor", "own_doc2")
        r = client.post(f"/appointments/{appt.id}/start-consultation")
        assert r.status_code == 403

    def test_patient_cannot_cancel_another_patients_appointment(self, client, db_session):
        doc_pid  = register_user(client, "doctor",  "own_doc3")
        pat1_pid = register_user(client, "patient", "own_pat2")
        appt = _seed(db_session, doc_pid, pat1_pid, AppointmentStatus.booked)
        # Register pat2; their cookies are now active
        register_user(client, "patient", "own_pat3")
        r = client.post(f"/appointments/{appt.id}/cancel")
        assert r.status_code == 403

    def test_patient_can_cancel_own_appointment(self, client, db_session):
        doc_pid = register_user(client, "doctor",  "own_doc4")
        pat_pid = register_user(client, "patient", "own_pat4")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked)
        login(client, "own_pat4")
        r = client.post(f"/appointments/{appt.id}/cancel")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "cancelled"

    def test_receptionist_can_cancel_any_appointment(self, client, db_session):
        doc_pid = register_user(client, "doctor",       "own_doc5")
        pat_pid = register_user(client, "patient",      "own_pat5")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked)
        register_user(client, "receptionist", "own_rec1")
        r = client.post(f"/appointments/{appt.id}/cancel")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "cancelled"


# ══════════════════════════════════════════════════════════════════════════════
# TestQueueEndpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestQueueEndpoints:
    def test_receptionist_queue_returns_todays_appointments(self, client, db_session):
        doc_pid = register_user(client, "doctor",       "q_doc1")
        pat_pid = register_user(client, "patient",      "q_pat1")
        register_user(client, "receptionist", "q_rec1")
        today = datetime.now(tz=timezone.utc).date()
        _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked, today)
        r = client.get("/appointments/queue/today")
        assert r.status_code == 200, r.text
        assert len(r.json()) >= 1
        assert r.json()[0]["status"] == "booked"

    def test_receptionist_queue_excludes_other_dates(self, client, db_session):
        doc_pid = register_user(client, "doctor",       "q_doc2")
        pat_pid = register_user(client, "patient",      "q_pat2")
        register_user(client, "receptionist", "q_rec2")
        yesterday = (datetime.now(tz=timezone.utc) - timedelta(days=1)).date()
        _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked, yesterday)
        r = client.get("/appointments/queue/today")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_receptionist_queue_sorted_by_lifecycle_order(self, client, db_session):
        doc_pid = register_user(client, "doctor",  "q_doc3")
        pat_pid = register_user(client, "patient", "q_pat3")
        register_user(client, "receptionist", "q_rec3")
        today = datetime.now(tz=timezone.utc).date()

        # Use different hours to avoid UNIQUE(doctor_id, slot_start) collision
        start1 = datetime(today.year, today.month, today.day, 9,  0, tzinfo=timezone.utc)
        start2 = datetime(today.year, today.month, today.day, 10, 0, tzinfo=timezone.utc)

        from app.models.scheduling import AppointmentSlot as _Slot
        from app.models.appointment import Appointment as _Appt
        slot1 = _Slot(doctor_id=doc_pid, slot_start=start1, slot_end=start1 + timedelta(hours=1))
        slot2 = _Slot(doctor_id=doc_pid, slot_start=start2, slot_end=start2 + timedelta(hours=1))
        db_session.add(slot1); db_session.add(slot2); db_session.flush()

        appt1 = _Appt(patient_id=pat_pid, doctor_id=doc_pid, slot_id=slot1.id,
                      status=AppointmentStatus.cancelled)
        appt2 = _Appt(patient_id=pat_pid, doctor_id=doc_pid, slot_id=slot2.id,
                      status=AppointmentStatus.booked)
        db_session.add(appt1); db_session.add(appt2); db_session.commit()

        r = client.get("/appointments/queue/today")
        assert r.status_code == 200
        statuses = [x["status"] for x in r.json()]
        assert statuses.index("booked") < statuses.index("cancelled")

    def test_doctor_queue_only_shows_own_appointments(self, client, db_session):
        doc1_pid = register_user(client, "doctor",  "q_doc4")
        pat_pid  = register_user(client, "patient", "q_pat4")
        doc2_pid = register_user(client, "doctor",  "q_doc5")
        today = datetime.now(tz=timezone.utc).date()
        appt1 = _seed(db_session, doc1_pid, pat_pid, AppointmentStatus.booked, today)
        appt2 = _seed(db_session, doc2_pid, pat_pid, AppointmentStatus.booked, today)
        # doc2 is logged in (last register)
        r = client.get("/appointments/queue/mine")
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert appt1.id not in ids
        assert appt2.id in ids

    def test_doctor_queue_accepts_date_override(self, client, db_session):
        doc_pid = register_user(client, "doctor",  "q_doc6")
        pat_pid = register_user(client, "patient", "q_pat5")
        login(client, "q_doc6")
        yesterday = (datetime.now(tz=timezone.utc) - timedelta(days=1)).date()
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked, yesterday)
        r = client.get(f"/appointments/queue/mine?date={yesterday.isoformat()}")
        assert r.status_code == 200
        assert appt.id in [x["id"] for x in r.json()]

    def test_queue_items_have_correct_fields(self, client, db_session):
        doc_pid = register_user(client, "doctor",  "q_doc7")
        pat_pid = register_user(client, "patient", "q_pat6")
        login(client, "q_doc7")
        _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked)
        r = client.get("/appointments/queue/mine")
        assert r.status_code == 200
        item = r.json()[0]
        for f in ("id", "status", "patient_name", "doctor_name", "slot_start", "slot_end"):
            assert f in item, f"Missing field: {f}"


# ══════════════════════════════════════════════════════════════════════════════
# TestE2EHttpGuard
# ══════════════════════════════════════════════════════════════════════════════

class TestE2EHttpGuard:
    def test_check_in_twice_returns_409(self, client, db_session):
        doc_pid = register_user(client, "doctor",       "e2e_doc1")
        pat_pid = register_user(client, "patient",      "e2e_pat1")
        register_user(client, "receptionist", "e2e_rec1")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked)

        r1 = client.post(f"/appointments/{appt.id}/check-in")
        assert r1.status_code == 200, r1.text

        r2 = client.post(f"/appointments/{appt.id}/check-in")
        assert r2.status_code == 409
        body = r2.json()
        assert body["current_status"] == "checked_in"
        assert body["attempted_status"] == "checked_in"

    def test_start_consultation_on_booked_returns_409(self, client, db_session):
        doc_pid = register_user(client, "doctor",  "e2e_doc2")
        pat_pid = register_user(client, "patient", "e2e_pat2")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked)
        login(client, "e2e_doc2")
        r = client.post(f"/appointments/{appt.id}/start-consultation")
        assert r.status_code == 409
        body = r.json()
        assert body["current_status"] == "booked"
        assert body["attempted_status"] == "in_consultation"

    def test_cancel_already_cancelled_returns_409(self, client, db_session):
        doc_pid = register_user(client, "doctor",       "e2e_doc3")
        pat_pid = register_user(client, "patient",      "e2e_pat3")
        register_user(client, "receptionist", "e2e_rec2")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.cancelled)
        r = client.post(f"/appointments/{appt.id}/cancel")
        assert r.status_code == 409
        assert r.json()["current_status"] == "cancelled"

    def test_full_lifecycle_happy_path(self, client, db_session):
        doc_pid = register_user(client, "doctor",  "e2e_doc4")
        pat_pid = register_user(client, "patient", "e2e_pat4")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.booked)

        register_user(client, "receptionist", "e2e_rec3")
        r1 = client.post(f"/appointments/{appt.id}/check-in")
        assert r1.status_code == 200, r1.text
        assert r1.json()["status"] == "checked_in"

        login(client, "e2e_doc4")
        r2 = client.post(f"/appointments/{appt.id}/start-consultation")
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "in_consultation"

    def test_409_body_structure(self, client, db_session):
        doc_pid = register_user(client, "doctor",       "e2e_doc5")
        pat_pid = register_user(client, "patient",      "e2e_pat5")
        register_user(client, "receptionist", "e2e_rec4")
        appt = _seed(db_session, doc_pid, pat_pid, AppointmentStatus.cancelled)
        r = client.post(f"/appointments/{appt.id}/check-in")
        assert r.status_code == 409
        body = r.json()
        for key in ("detail", "current_status", "attempted_status"):
            assert key in body
        assert str(appt.id) in body["detail"]

    def test_nonexistent_appointment_returns_404(self, client):
        register_user(client, "receptionist", "e2e_rec5")
        r = client.post("/appointments/999999/check-in")
        assert r.status_code == 404
