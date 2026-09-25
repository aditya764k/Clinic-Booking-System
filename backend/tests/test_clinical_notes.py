"""
Integration tests for Module 5: Doctor Console & AI-Assisted Clinical Notes.

Test groups (a–h per spec)
--------------------------
a. Draft success path — mock Gemini returns valid structured response
b. Draft AI timeout path — 502 returned, shorthand still persisted
c. Malformed JSON path — retry-once triggered; AIDraftGenerationError handled
d. Finalize — AI-assisted and fully manual (two separate cases)
e. Complete-visit — three sub-cases (no note / draft-only / finalized)
f. Ownership — wrong doctor → 403 for each endpoint
g. Wrong state — appointment not in_consultation → 409 for each endpoint
h. Full manual path — no draft, straight to finalize → complete end-to-end
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from starlette.testclient import TestClient

from app.models.appointment import Appointment, AppointmentStatus, ClinicalNote
from app.models.scheduling import AppointmentSlot
from app.schemas.clinical_note import AIDraftOut
from app.core.exceptions import AIDraftGenerationError


# ── Helpers (same pattern as test_appointment_state.py) ──────────────────────

def register_user(client: TestClient, role: str, suffix: str) -> int | None:
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
    client.post("/auth/login",
                json={"email": f"{suffix}@t.com", "password": "Str0ngPass!"})


def _seed_appointment(
    db, doctor_id: int, patient_id: int,
    s: AppointmentStatus,
) -> Appointment:
    today = datetime.now(tz=timezone.utc).date()
    start = datetime(today.year, today.month, today.day, 10, 0, tzinfo=timezone.utc)
    slot = AppointmentSlot(doctor_id=doctor_id,
                           slot_start=start,
                           slot_end=start + timedelta(hours=1))
    db.add(slot); db.flush()
    appt = Appointment(patient_id=patient_id, doctor_id=doctor_id,
                       slot_id=slot.id, status=s)
    db.add(appt); db.commit(); db.refresh(appt)
    return appt


_GOOD_DRAFT = AIDraftOut(
    chief_complaint="Fever for 3 days with dry cough",
    assessment="Likely viral URI. Lungs clear.",
    suggested_rx="Paracetamol 500mg TDS for 3 days, rest, hydration.",
)

_MOCK_PATH = "app.api.clinical_notes.generate_clinical_draft"


# ══════════════════════════════════════════════════════════════════════════════
# a. Draft success path
# ══════════════════════════════════════════════════════════════════════════════

class TestDraftSuccess:
    def test_draft_returns_200_and_persists(self, client, db_session):
        doc_pid = register_user(client, "doctor", "ds_doc1")
        pat_pid = register_user(client, "patient", "ds_pat1")
        login(client, "ds_doc1")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, return_value=_GOOD_DRAFT):
            r = client.post(
                f"/appointments/{appt.id}/clinical-note/draft",
                json={"shorthand_input": "fever 3d, dry cough, temp 38.5C"},
            )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["chief_complaint"] == _GOOD_DRAFT.chief_complaint
        assert body["assessment"] == _GOOD_DRAFT.assessment
        assert body["suggested_rx"] == _GOOD_DRAFT.suggested_rx

        # Verify DB persistence
        db_session.expire_all()
        note = db_session.query(ClinicalNote).filter_by(appointment_id=appt.id).first()
        assert note is not None
        assert note.shorthand_input == "fever 3d, dry cough, temp 38.5C"
        assert note.ai_draft_json is not None
        assert note.ai_draft_json["chief_complaint"] == _GOOD_DRAFT.chief_complaint

    def test_draft_rejects_empty_shorthand(self, client, db_session):
        doc_pid = register_user(client, "doctor", "ds_doc2")
        pat_pid = register_user(client, "patient", "ds_pat2")
        login(client, "ds_doc2")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, return_value=_GOOD_DRAFT):
            r = client.post(
                f"/appointments/{appt.id}/clinical-note/draft",
                json={"shorthand_input": "   "},
            )
        assert r.status_code == 422

    def test_second_draft_updates_not_duplicates(self, client, db_session):
        """Calling /draft twice must update the same row, not create two rows."""
        doc_pid = register_user(client, "doctor", "ds_doc3")
        pat_pid = register_user(client, "patient", "ds_pat3")
        login(client, "ds_doc3")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, return_value=_GOOD_DRAFT):
            client.post(f"/appointments/{appt.id}/clinical-note/draft",
                        json={"shorthand_input": "first attempt"})
            client.post(f"/appointments/{appt.id}/clinical-note/draft",
                        json={"shorthand_input": "second attempt"})

        db_session.expire_all()
        count = db_session.query(ClinicalNote).filter_by(appointment_id=appt.id).count()
        assert count == 1
        note = db_session.query(ClinicalNote).filter_by(appointment_id=appt.id).first()
        assert note.shorthand_input == "second attempt"


# ══════════════════════════════════════════════════════════════════════════════
# b. Draft AI timeout path
# ══════════════════════════════════════════════════════════════════════════════

class TestDraftAIFailure:
    def test_timeout_returns_502_not_500(self, client, db_session):
        doc_pid = register_user(client, "doctor", "af_doc1")
        pat_pid = register_user(client, "patient", "af_pat1")
        login(client, "af_doc1")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, side_effect=AIDraftGenerationError(
            cause_type="timeout", message="timed out after 12s"
        )):
            r = client.post(
                f"/appointments/{appt.id}/clinical-note/draft",
                json={"shorthand_input": "fever 3d"},
            )

        assert r.status_code == 502
        body = r.json()
        assert "detail" in body

    def test_timeout_shorthand_still_persisted(self, client, db_session):
        doc_pid = register_user(client, "doctor", "af_doc2")
        pat_pid = register_user(client, "patient", "af_pat2")
        login(client, "af_doc2")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, side_effect=AIDraftGenerationError(
            cause_type="timeout", message="timed out"
        )):
            client.post(f"/appointments/{appt.id}/clinical-note/draft",
                        json={"shorthand_input": "saved despite timeout"})

        db_session.expire_all()
        note = db_session.query(ClinicalNote).filter_by(appointment_id=appt.id).first()
        assert note is not None
        assert note.shorthand_input == "saved despite timeout"
        assert note.ai_draft_json is None  # draft not saved

    def test_api_error_returns_502(self, client, db_session):
        doc_pid = register_user(client, "doctor", "af_doc3")
        pat_pid = register_user(client, "patient", "af_pat3")
        login(client, "af_doc3")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, side_effect=AIDraftGenerationError(
            cause_type="api_error", message="HTTP 429 rate limit"
        )):
            r = client.post(f"/appointments/{appt.id}/clinical-note/draft",
                            json={"shorthand_input": "test"})

        assert r.status_code == 502


# ══════════════════════════════════════════════════════════════════════════════
# c. Malformed JSON path
# ══════════════════════════════════════════════════════════════════════════════

class TestDraftMalformedJSON:
    def test_malformed_response_returns_502_gracefully(self, client, db_session):
        doc_pid = register_user(client, "doctor", "mj_doc1")
        pat_pid = register_user(client, "patient", "mj_pat1")
        login(client, "mj_doc1")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, side_effect=AIDraftGenerationError(
            cause_type="malformed_response",
            message="Gemini returned malformed JSON on both attempts",
        )):
            r = client.post(f"/appointments/{appt.id}/clinical-note/draft",
                            json={"shorthand_input": "fever cough"})

        assert r.status_code == 502
        assert r.status_code != 500  # must not be an unhandled server error

    def test_malformed_response_shorthand_saved(self, client, db_session):
        doc_pid = register_user(client, "doctor", "mj_doc2")
        pat_pid = register_user(client, "patient", "mj_pat2")
        login(client, "mj_doc2")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, side_effect=AIDraftGenerationError(
            cause_type="malformed_response", message="bad json"
        )):
            client.post(f"/appointments/{appt.id}/clinical-note/draft",
                        json={"shorthand_input": "shorthand to keep"})

        db_session.expire_all()
        note = db_session.query(ClinicalNote).filter_by(appointment_id=appt.id).first()
        assert note is not None
        assert note.shorthand_input == "shorthand to keep"
        assert note.ai_draft_json is None


# ══════════════════════════════════════════════════════════════════════════════
# d. Finalize — AI-assisted and manual
# ══════════════════════════════════════════════════════════════════════════════

class TestFinalize:
    def test_finalize_after_draft(self, client, db_session):
        """d1: AI-assisted path — draft first, then finalize."""
        doc_pid = register_user(client, "doctor", "fn_doc1")
        pat_pid = register_user(client, "patient", "fn_pat1")
        login(client, "fn_doc1")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, return_value=_GOOD_DRAFT):
            client.post(f"/appointments/{appt.id}/clinical-note/draft",
                        json={"shorthand_input": "fever 3d"})

        r = client.post(
            f"/appointments/{appt.id}/clinical-note/finalize",
            json={
                "final_chief_complaint": "Fever for 3 days (edited)",
                "final_assessment": "Viral URI confirmed",
                "final_suggested_rx": "Paracetamol 500mg TDS",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["final_chief_complaint"] == "Fever for 3 days (edited)"
        assert body["finalized_at"] is not None
        assert body["finalized_by_doctor_id"] == doc_pid

    def test_finalize_without_draft(self, client, db_session):
        """d2: Manual path — finalize with no prior /draft call.
        ai_draft_json must stay null throughout.
        """
        doc_pid = register_user(client, "doctor", "fn_doc2")
        pat_pid = register_user(client, "patient", "fn_pat2")
        login(client, "fn_doc2")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        r = client.post(
            f"/appointments/{appt.id}/clinical-note/finalize",
            json={
                "final_chief_complaint": "Headache — typed manually",
                "final_assessment": "Tension headache",
                "final_suggested_rx": "Ibuprofen 400mg as needed",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ai_draft_json"] is None  # no draft was ever generated
        assert body["final_chief_complaint"] == "Headache — typed manually"
        assert body["finalized_at"] is not None


# ══════════════════════════════════════════════════════════════════════════════
# e. Complete-visit — three sub-cases
# ══════════════════════════════════════════════════════════════════════════════

class TestCompleteVisit:
    def test_complete_without_any_note_returns_409(self, client, db_session):
        doc_pid = register_user(client, "doctor", "cv_doc1")
        pat_pid = register_user(client, "patient", "cv_pat1")
        login(client, "cv_doc1")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        r = client.post(f"/appointments/{appt.id}/complete")
        assert r.status_code == 409
        assert "clinical note" in r.json()["detail"].lower()

    def test_complete_with_draft_only_returns_409(self, client, db_session):
        """Draft exists but finalized_at is null — must be blocked."""
        doc_pid = register_user(client, "doctor", "cv_doc2")
        pat_pid = register_user(client, "patient", "cv_pat2")
        login(client, "cv_doc2")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        with patch(_MOCK_PATH, return_value=_GOOD_DRAFT):
            client.post(f"/appointments/{appt.id}/clinical-note/draft",
                        json={"shorthand_input": "fever"})

        r = client.post(f"/appointments/{appt.id}/complete")
        assert r.status_code == 409

    def test_complete_after_finalize_succeeds(self, client, db_session):
        """e3: Full success path — finalized note → complete."""
        doc_pid = register_user(client, "doctor", "cv_doc3")
        pat_pid = register_user(client, "patient", "cv_pat3")
        login(client, "cv_doc3")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        client.post(
            f"/appointments/{appt.id}/clinical-note/finalize",
            json={"final_chief_complaint": "X", "final_assessment": "Y", "final_suggested_rx": "Z"},
        )
        r = client.post(f"/appointments/{appt.id}/complete")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "completed"

        # Verify completed_at was set (from Module 4 transition_appointment)
        db_session.expire_all()
        updated = db_session.get(Appointment, appt.id)
        assert updated.completed_at is not None


# ══════════════════════════════════════════════════════════════════════════════
# f. Ownership — wrong doctor → 403
# ══════════════════════════════════════════════════════════════════════════════

class TestOwnership:
    def test_wrong_doctor_draft_returns_403(self, client, db_session):
        doc1_pid = register_user(client, "doctor", "ow_doc1")
        pat_pid   = register_user(client, "patient", "ow_pat1")
        appt = _seed_appointment(db_session, doc1_pid, pat_pid, AppointmentStatus.in_consultation)

        # Register doc2 — their cookies are now active
        register_user(client, "doctor", "ow_doc2")
        r = client.post(f"/appointments/{appt.id}/clinical-note/draft",
                        json={"shorthand_input": "test"})
        assert r.status_code == 403

    def test_wrong_doctor_finalize_returns_403(self, client, db_session):
        doc1_pid = register_user(client, "doctor", "ow_doc3")
        pat_pid   = register_user(client, "patient", "ow_pat2")
        appt = _seed_appointment(db_session, doc1_pid, pat_pid, AppointmentStatus.in_consultation)

        register_user(client, "doctor", "ow_doc4")
        r = client.post(
            f"/appointments/{appt.id}/clinical-note/finalize",
            json={"final_chief_complaint": "X", "final_assessment": "Y", "final_suggested_rx": "Z"},
        )
        assert r.status_code == 403

    def test_wrong_doctor_complete_returns_403(self, client, db_session):
        doc1_pid = register_user(client, "doctor", "ow_doc5")
        pat_pid   = register_user(client, "patient", "ow_pat3")
        appt = _seed_appointment(db_session, doc1_pid, pat_pid, AppointmentStatus.in_consultation)

        register_user(client, "doctor", "ow_doc6")
        r = client.post(f"/appointments/{appt.id}/complete")
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# g. Wrong state — not in_consultation → 409
# ══════════════════════════════════════════════════════════════════════════════

class TestWrongState:
    def test_draft_on_checked_in_returns_409(self, client, db_session):
        doc_pid = register_user(client, "doctor", "ws_doc1")
        pat_pid = register_user(client, "patient", "ws_pat1")
        login(client, "ws_doc1")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.checked_in)

        with patch(_MOCK_PATH, return_value=_GOOD_DRAFT):
            r = client.post(f"/appointments/{appt.id}/clinical-note/draft",
                            json={"shorthand_input": "test"})
        assert r.status_code == 409

    def test_finalize_on_booked_returns_409(self, client, db_session):
        doc_pid = register_user(client, "doctor", "ws_doc2")
        pat_pid = register_user(client, "patient", "ws_pat2")
        login(client, "ws_doc2")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.booked)

        r = client.post(
            f"/appointments/{appt.id}/clinical-note/finalize",
            json={"final_chief_complaint": "X", "final_assessment": "Y", "final_suggested_rx": "Z"},
        )
        assert r.status_code == 409

    def test_complete_on_booked_returns_409(self, client, db_session):
        """complete endpoint checks for finalized note first → 409 (no note)
        even if we never even get to the state-transition guard."""
        doc_pid = register_user(client, "doctor", "ws_doc3")
        pat_pid = register_user(client, "patient", "ws_pat3")
        login(client, "ws_doc3")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.booked)

        r = client.post(f"/appointments/{appt.id}/complete")
        assert r.status_code == 409


# ══════════════════════════════════════════════════════════════════════════════
# h. Full manual path — no draft, direct finalize → complete
# ══════════════════════════════════════════════════════════════════════════════

class TestFullManualPath:
    def test_manual_path_end_to_end(self, client, db_session):
        """Confirms FR-DOC-07: the AI call is never required.
        No /draft call is made. Doctor goes straight to finalize then complete.
        The result must be a successfully COMPLETED appointment with a finalized note.
        """
        doc_pid = register_user(client, "doctor", "mp_doc1")
        pat_pid = register_user(client, "patient", "mp_pat1")
        login(client, "mp_doc1")
        appt = _seed_appointment(db_session, doc_pid, pat_pid, AppointmentStatus.in_consultation)

        # Step 1: Finalize directly (no draft ever called)
        r_fin = client.post(
            f"/appointments/{appt.id}/clinical-note/finalize",
            json={
                "final_chief_complaint": "Persistent cough — manual entry",
                "final_assessment": "Chronic cough, likely post-nasal drip",
                "final_suggested_rx": "Antihistamine + steam inhalation",
            },
        )
        assert r_fin.status_code == 200, r_fin.text
        fin_body = r_fin.json()
        assert fin_body["ai_draft_json"] is None
        assert fin_body["finalized_at"] is not None

        # Step 2: Complete the visit
        r_comp = client.post(f"/appointments/{appt.id}/complete")
        assert r_comp.status_code == 200, r_comp.text
        assert r_comp.json()["status"] == "completed"

        # Step 3: Verify DB state
        db_session.expire_all()
        final_appt = db_session.get(Appointment, appt.id)
        final_note = db_session.query(ClinicalNote).filter_by(appointment_id=appt.id).first()

        assert final_appt.status == AppointmentStatus.completed
        assert final_appt.completed_at is not None
        assert final_note.finalized_at is not None
        assert final_note.ai_draft_json is None  # AI was never involved
        assert final_note.final_chief_complaint == "Persistent cough — manual entry"
