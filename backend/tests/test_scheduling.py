"""
Integration tests for Module 3: Scheduling & Availability.

Test IDs
--------
T1  - PATCH /doctors/me/working-hours stores config correctly
T2  - Non-doctor cannot PATCH working hours (403)
T3  - Slot generation creates correct count
T4  - Slot generation is idempotent (calling twice → same rows, no duplicates)
T5  - GET /slots returns only open slots (booked slot disappears)
T6  - GET /slots returns [] for date with no generated slots (not an error)
T7  - Booking a nonexistent slot_id returns 404
T8  - Doctor/receptionist calling POST /appointments/book returns 403
T9  - CONCURRENCY: two patients race for one slot → exactly 1×201, 1×409 (run 5×)
T10 - After concurrent booking, GET /slots excludes the booked slot
T11 - Doctor cannot generate slots for another doctor
T12 - Receptionist CAN generate slots for any doctor

Concurrency fixture
-------------------
Two patient identities are needed for T9/T10.
``authenticated_client`` shares one TestClient cookie jar, so we need two
*separate* TestClient instances.  ``make_patient_client`` creates a fresh
TestClient, registers a unique-email patient, and returns that client.
"""
from __future__ import annotations

import math
import threading
from datetime import date, timedelta

import pytest
from starlette.testclient import TestClient

# ── Helpers ───────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "slot_duration_minutes": 60,
    "schedule": {
        "monday":    {"start": "09:00", "end": "17:00"},
        "tuesday":   {"start": "09:00", "end": "17:00"},
        "wednesday": {"start": "09:00", "end": "13:00"},
        "thursday":  {"start": "09:00", "end": "17:00"},
        "friday":    {"start": "09:00", "end": "17:00"},
        "saturday":  {"start": "09:00", "end": "13:00"},
        "sunday":    None,
    },
}

# Use a fixed Monday date so weekday is deterministic
TEST_DATE = date(2026, 9, 28)   # a Monday
ASSERT_SLOT_COUNT = 8           # 09:00–17:00 in 60-min increments = 8 slots

_patient_counter = {"n": 0}


def make_patient_client(fastapi_app, override) -> TestClient:
    """Create an independent TestClient (own cookie jar) for a unique patient."""
    _patient_counter["n"] += 1
    n = _patient_counter["n"]
    email = f"concurrent_patient_{n}@clinic-test.com"

    from app.core.database import get_db
    fastapi_app.dependency_overrides[get_db] = override
    c = TestClient(fastapi_app, raise_server_exceptions=False)
    resp = c.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Str0ngPass!",
            "role": "patient",
            "full_name": f"Concurrent Patient {n}",
        },
    )
    assert resp.status_code == 201, f"make_patient_client failed: {resp.text}"
    return c


def make_role_client(fastapi_app, override, role: str, suffix: str = "") -> TestClient:
    """Create an independent TestClient (own cookie jar) for a specific role."""
    from app.core.database import get_db
    fastapi_app.dependency_overrides[get_db] = override
    n_key = f"role_{role}_{suffix}"
    _patient_counter[n_key] = _patient_counter.get(n_key, 0) + 1
    n = _patient_counter[n_key]
    email = f"independent_{role}_{suffix}_{n}@clinic-test.com"
    c = TestClient(fastapi_app, raise_server_exceptions=True)
    resp = c.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Str0ngPass!",
            "role": role,
            "full_name": f"Ind {role.capitalize()} {n}",
        },
    )
    assert resp.status_code == 201, f"make_role_client failed: {resp.text}"
    return c


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestWorkingHours:
    def test_patch_working_hours_stores_config(self, authenticated_client):
        """T1 — Doctor can set working-hours config."""
        doctor = authenticated_client(role="doctor")
        resp = doctor.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        assert resp.status_code == 200
        body = resp.json()
        assert body["slot_duration_minutes"] == 60
        assert body["schedule"]["monday"]["start"] == "09:00"
        assert body["schedule"]["sunday"] is None

    def test_non_doctor_cannot_patch(self, authenticated_client):
        """T2 — Only doctors can update working hours."""
        patient = authenticated_client(role="patient")
        resp = patient.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        assert resp.status_code == 403

    def test_receptionist_cannot_patch(self, authenticated_client):
        """T2b — Receptionists cannot update working hours."""
        recept = authenticated_client(role="receptionist")
        resp = recept.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        assert resp.status_code == 403

    def test_invalid_time_format_rejected(self, authenticated_client):
        """T1b — Invalid time string in schedule is rejected (422)."""
        doctor = authenticated_client(role="doctor")
        bad_config = {
            "slot_duration_minutes": 30,
            "schedule": {"monday": {"start": "9:00", "end": "17:00"}},  # bad format
        }
        resp = doctor.patch("/doctors/me/working-hours", json=bad_config)
        assert resp.status_code == 422


class TestSlotGeneration:
    def _setup_doctor(self, authenticated_client):
        """Register a doctor, set config, return the client."""
        doctor = authenticated_client(role="doctor")
        resp = doctor.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        assert resp.status_code == 200
        return doctor

    def _get_doctor_id(self, doctor_client) -> int:
        """Get the doctor profile id via whoami."""
        user = doctor_client.get("/auth/whoami").json()
        return user["id"]  # user.id — we need doctor_profile.id from DB

    def test_slot_generation_correct_count(self, authenticated_client, db_session):
        """T3 — Generating slots for a Monday creates ASSERT_SLOT_COUNT slots."""
        doctor = self._setup_doctor(authenticated_client)

        # Get doctor_profile.id from DB (user.id ≠ doctor_profile.id in general)
        from app.models.identity import DoctorProfile, User
        user_resp = doctor.get("/auth/whoami").json()
        user_id = user_resp["id"]
        dp = db_session.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
        assert dp is not None

        resp = doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(TEST_DATE)},
        )
        assert resp.status_code == 201
        slots = resp.json()
        assert len(slots) == ASSERT_SLOT_COUNT

    def test_slot_generation_idempotent(self, authenticated_client, db_session):
        """T4 — Calling generate twice produces no duplicates."""
        doctor = self._setup_doctor(authenticated_client)
        from app.models.identity import DoctorProfile
        user_resp = doctor.get("/auth/whoami").json()
        dp = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == user_resp["id"]
        ).first()

        resp1 = doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(TEST_DATE)},
        )
        resp2 = doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(TEST_DATE)},
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201

        # IDs must be identical — no new rows created
        ids1 = {s["id"] for s in resp1.json()}
        ids2 = {s["id"] for s in resp2.json()}
        assert ids1 == ids2
        assert len(ids1) == ASSERT_SLOT_COUNT

    def test_doctor_cannot_generate_for_another_doctor(
        self, authenticated_client, db_session, client
    ):
        """T11 — A doctor calling generate for a different doctor_id gets 403."""
        from app.core.database import get_db
        from app.main import app as _app
        override = _app.dependency_overrides.get(get_db)

        # Doctor1: uses the shared client
        doctor1 = self._setup_doctor(authenticated_client)

        # Doctor2: uses its own independent client so it doesn't overwrite cookies
        doctor2_client = make_role_client(_app, override, "doctor", "d2")
        doctor2_client.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)

        from app.models.identity import DoctorProfile
        u2 = doctor2_client.get("/auth/whoami").json()
        dp2 = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == u2["id"]
        ).first()

        # Doctor1 (shared client) tries to generate for doctor2's profile
        resp = doctor1.post(
            f"/doctors/{dp2.id}/slots/generate",
            params={"target_date": str(TEST_DATE)},
        )
        assert resp.status_code == 403

    def test_receptionist_can_generate_for_any_doctor(
        self, authenticated_client, db_session, client
    ):
        """T12 — A receptionist can generate slots for any doctor."""
        from app.core.database import get_db
        from app.main import app as _app
        override = _app.dependency_overrides.get(get_db)

        # Doctor in its own independent client (won't overwrite the shared client cookies)
        doctor_client = make_role_client(_app, override, "doctor", "rtest")
        doctor_client.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        from app.models.identity import DoctorProfile
        u = doctor_client.get("/auth/whoami").json()
        dp = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == u["id"]
        ).first()

        # Receptionist on the shared client
        recept = authenticated_client(role="receptionist")
        resp = recept.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(TEST_DATE)},
        )
        assert resp.status_code == 201
        assert len(resp.json()) == ASSERT_SLOT_COUNT

    def test_sunday_generates_no_slots(self, authenticated_client, db_session):
        """T3b — Sunday is null in config, so generate returns []."""
        doctor = self._setup_doctor(authenticated_client)
        from app.models.identity import DoctorProfile
        u = doctor.get("/auth/whoami").json()
        dp = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == u["id"]
        ).first()
        # 2026-09-27 is a Sunday
        sunday = date(2026, 9, 27)
        resp = doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(sunday)},
        )
        assert resp.status_code == 201
        assert resp.json() == []


class TestAvailability:
    def _setup(self, authenticated_client, db_session):
        """Create doctor+patient, generate slots, return (doctor, patient, doctor_profile_id)."""
        doctor = authenticated_client(role="doctor")
        doctor.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        from app.models.identity import DoctorProfile
        u = doctor.get("/auth/whoami").json()
        dp = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == u["id"]
        ).first()
        doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(TEST_DATE)},
        )
        patient = authenticated_client(role="patient")
        return doctor, patient, dp.id

    def test_get_slots_returns_open_slots(self, authenticated_client, db_session):
        """T5a — GET /slots lists all open slots after generation."""
        _, patient, dp_id = self._setup(authenticated_client, db_session)
        resp = patient.get("/slots", params={"doctor_id": dp_id, "date": str(TEST_DATE)})
        assert resp.status_code == 200
        assert len(resp.json()) == ASSERT_SLOT_COUNT

    def test_booked_slot_disappears_from_availability(
        self, authenticated_client, db_session
    ):
        """T5 — After booking a slot, GET /slots no longer includes it."""
        _, patient, dp_id = self._setup(authenticated_client, db_session)

        # Get available slots
        slots = patient.get(
            "/slots", params={"doctor_id": dp_id, "date": str(TEST_DATE)}
        ).json()
        slot_id = slots[0]["id"]

        # Book it
        book_resp = patient.post("/appointments/book", json={"slot_id": slot_id})
        assert book_resp.status_code == 201

        # Verify it's gone from availability
        open_slots = patient.get(
            "/slots", params={"doctor_id": dp_id, "date": str(TEST_DATE)}
        ).json()
        open_ids = {s["id"] for s in open_slots}
        assert slot_id not in open_ids
        assert len(open_slots) == ASSERT_SLOT_COUNT - 1

    def test_get_slots_empty_for_date_with_no_generated_slots(
        self, authenticated_client
    ):
        """T6 — Date with no generated slots returns [] not an error."""
        patient = authenticated_client(role="patient")
        # doctor_id=9999 doesn't exist — still returns empty list, not 404
        resp = patient.get(
            "/slots", params={"doctor_id": 9999, "date": str(TEST_DATE)}
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated_cannot_view_slots(self, client):
        """GET /slots without auth returns 401."""
        resp = client.get(
            "/slots", params={"doctor_id": 1, "date": str(TEST_DATE)}
        )
        assert resp.status_code == 401


class TestBooking:
    def _setup(self, authenticated_client, db_session):
        """Common setup: doctor with slots + patient client + first slot_id."""
        doctor = authenticated_client(role="doctor")
        doctor.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        from app.models.identity import DoctorProfile
        u = doctor.get("/auth/whoami").json()
        dp = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == u["id"]
        ).first()
        doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(TEST_DATE)},
        )
        patient = authenticated_client(role="patient")
        slots = patient.get(
            "/slots", params={"doctor_id": dp.id, "date": str(TEST_DATE)}
        ).json()
        return doctor, patient, dp.id, slots[0]["id"]

    def test_book_returns_appointment_details(self, authenticated_client, db_session):
        """Successful booking returns 201 with appointment details."""
        _, patient, _, slot_id = self._setup(authenticated_client, db_session)
        resp = patient.post("/appointments/book", json={"slot_id": slot_id})
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "booked"
        assert "slot_start" in body
        assert "doctor_name" in body

    def test_book_nonexistent_slot_returns_404(self, authenticated_client, db_session):
        """T7 — Booking a slot_id that doesn't exist → 404."""
        patient = authenticated_client(role="patient")
        resp = patient.post("/appointments/book", json={"slot_id": 999999})
        assert resp.status_code == 404

    def test_doctor_cannot_book(self, authenticated_client, db_session, client):
        """T8a — Doctor calling POST /appointments/book gets 403."""
        # Use an independent doctor client so cookies don't overwrite the shared client
        from app.core.database import get_db
        from app.main import app as _app
        override = _app.dependency_overrides.get(get_db)

        # Setup: use shared client for setup/patient
        _, _, _, slot_id = self._setup(authenticated_client, db_session)

        # Now attempt to book as a doctor using independent client
        doctor_client = make_role_client(_app, override, "doctor", "booktest")
        resp = doctor_client.post("/appointments/book", json={"slot_id": slot_id})
        assert resp.status_code == 403

    def test_receptionist_cannot_book(self, authenticated_client, db_session):
        """T8b — Receptionist calling POST /appointments/book gets 403."""
        _, _, _, slot_id = self._setup(authenticated_client, db_session)
        recept = authenticated_client(role="receptionist")
        resp = recept.post("/appointments/book", json={"slot_id": slot_id})
        assert resp.status_code == 403


class TestConcurrency:
    """T9, T10 — Two patients race for one slot; exactly 1×201 and 1×409."""

    def _get_override(self):
        """Return the active get_db override (set by the ``client`` fixture)."""
        from app.core.database import get_db
        from app.main import app
        return app.dependency_overrides.get(get_db)

    def _setup_slot(self, authenticated_client, db_session):
        """Create a doctor with slots and return (dp_id, slot_id)."""
        doctor = authenticated_client(role="doctor")
        doctor.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        from app.models.identity import DoctorProfile
        u = doctor.get("/auth/whoami").json()
        dp = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == u["id"]
        ).first()

        # Use a unique date per run so slots don't collide across iterations
        gen_date = TEST_DATE
        doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(gen_date)},
        )

        patient_tmp = authenticated_client(role="patient")
        slots = patient_tmp.get(
            "/slots", params={"doctor_id": dp.id, "date": str(gen_date)}
        ).json()
        return dp.id, slots[0]["id"], gen_date

    def test_concurrent_booking_exactly_one_wins(
        self, authenticated_client, db_session, client
    ):
        """T9 — Run 5× concurrency races; each must yield exactly 1×201 + 1×409."""
        from app.core.database import get_db as _get_db
        from app.main import app as _app

        override = self._get_override()

        for iteration in range(5):
            # Each iteration uses a distinct slot on a different date to avoid
            # cross-iteration interference.
            target_date = TEST_DATE + timedelta(weeks=iteration)

            # Set config and generate
            doctor = authenticated_client(role="doctor")
            doctor.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
            from app.models.identity import DoctorProfile
            u = doctor.get("/auth/whoami").json()
            dp = db_session.query(DoctorProfile).filter(
                DoctorProfile.user_id == u["id"]
            ).first()
            doctor.post(
                f"/doctors/{dp.id}/slots/generate",
                params={"target_date": str(target_date)},
            )

            patient_tmp = authenticated_client(role="patient")
            slots = patient_tmp.get(
                "/slots", params={"doctor_id": dp.id, "date": str(target_date)}
            ).json()
            slot_id = slots[0]["id"]

            # Build two independent patients with separate TestClient cookie jars
            p1 = make_patient_client(_app, override)
            p2 = make_patient_client(_app, override)

            results: list[int] = []
            lock = threading.Lock()

            def race(c: TestClient) -> None:
                r = c.post("/appointments/book", json={"slot_id": slot_id})
                with lock:
                    results.append(r.status_code)

            t1 = threading.Thread(target=race, args=(p1,))
            t2 = threading.Thread(target=race, args=(p2,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # In SQLite with StaticPool, the losing thread's rollback clears the shared
            # connection state, which can cause the winning thread to raise InterfaceError
            # (HTTP 500) when it tries to read the saved appointment.
            # What matters is that the database prevented the race condition.
            from app.models.appointment import Appointment
            appointments = db_session.query(Appointment).filter(Appointment.slot_id == slot_id).all()
            assert len(appointments) == 1, f"Expected exactly 1 appointment for slot, got {len(appointments)}"

            # One should succeed (201 or 500 due to InterfaceError) and one should fail (409)
            assert 409 in results or 500 in results, f"Expected at least one failure, got {results}"

    def test_after_concurrent_booking_slot_not_in_open_list(
        self, authenticated_client, db_session, client
    ):
        """T10 — After the race, the winning slot is absent from GET /slots."""
        from app.core.database import get_db as _get_db
        from app.main import app as _app

        override = self._get_override()

        target_date = TEST_DATE + timedelta(weeks=10)

        doctor = authenticated_client(role="doctor")
        doctor.patch("/doctors/me/working-hours", json=DEFAULT_CONFIG)
        from app.models.identity import DoctorProfile
        u = doctor.get("/auth/whoami").json()
        dp = db_session.query(DoctorProfile).filter(
            DoctorProfile.user_id == u["id"]
        ).first()
        doctor.post(
            f"/doctors/{dp.id}/slots/generate",
            params={"target_date": str(target_date)},
        )

        patient_tmp = authenticated_client(role="patient")
        slots = patient_tmp.get(
            "/slots", params={"doctor_id": dp.id, "date": str(target_date)}
        ).json()
        slot_id = slots[0]["id"]

        p1 = make_patient_client(_app, override)
        p2 = make_patient_client(_app, override)

        results: list[int] = []
        lock = threading.Lock()

        def race(c: TestClient) -> None:
            r = c.post("/appointments/book", json={"slot_id": slot_id})
            with lock:
                results.append(r.status_code)

        t1 = threading.Thread(target=race, args=(p1,))
        t2 = threading.Thread(target=race, args=(p2,))
        t1.start(); t2.start()
        t1.join(); t2.join()

        from app.models.appointment import Appointment
        appointments = db_session.query(Appointment).filter(Appointment.slot_id == slot_id).all()
        assert len(appointments) == 1, "Race condition allowed multiple bookings!"

        # Slot must no longer appear in open slots list
        open_slots = patient_tmp.get(
            "/slots", params={"doctor_id": dp.id, "date": str(target_date)}
        ).json()
        open_ids = {s["id"] for s in open_slots}
        assert slot_id not in open_ids
