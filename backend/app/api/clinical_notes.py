"""
Doctor Console & Clinical Notes API endpoints.

Endpoints
---------
POST /appointments/{appointment_id}/clinical-note/draft
    Doctor submits shorthand → AI generates a structured draft.
    Returns AIDraftOut on success; 502 on AI failure (shorthand still persisted).

POST /appointments/{appointment_id}/clinical-note/finalize
    Doctor submits the final (possibly edited) clinical note.
    THIS IS THE ONLY ENDPOINT PERMITTED TO WRITE the final_ columns and
    finalized_by_doctor_id / finalized_at on clinical_notes rows.
    (Same single-writer discipline Module 4 established for appointments.status.)

POST /appointments/{appointment_id}/complete
    Doctor completes the visit.
    Guard: clinical note must exist AND be finalized (finalized_at != null).
    Delegates the status transition to transition_appointment() from Module 4.

Design notes
------------
- All three endpoints share the same ownership check pattern used by
  start_consultation() in app/api/appointment_state.py.
- Business-state checks (appointment must be IN_CONSULTATION; note must be
  finalized before completion) use plain HTTPException 409 — they are
  distinct from the state-machine guard in appointment_state.py, which
  handles LEGAL_TRANSITIONS enforcement.
- AIDraftGenerationError is allowed to propagate; it is caught by the global
  handler in app/main.py and converted to HTTP 502.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import AIDraftGenerationError
from app.models.appointment import Appointment, AppointmentStatus, ClinicalNote
from app.models.identity import DoctorProfile, User
from app.models.scheduling import AppointmentSlot
from app.schemas.clinical_note import (
    AIDraftOut,
    ClinicalNoteOut,
    DraftRequest,
    FinalizeNoteRequest,
)
from app.schemas.scheduling import AppointmentOut
from app.services.ai_notes import generate_clinical_draft
from app.services.appointment_state import transition_appointment
from app.api.appointment_state import _appointment_out  # reuse helper

logger = logging.getLogger(__name__)
router = APIRouter(tags=["clinical-notes"])


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _resolve_doctor(db: Session, current_user: User) -> DoctorProfile:
    """Resolve the calling user's DoctorProfile. Raises 404 if missing."""
    doctor: DoctorProfile | None = (
        db.query(DoctorProfile)
        .filter(DoctorProfile.user_id == current_user.id)
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for current user",
        )
    return doctor


def _get_appointment_with_ownership(
    db: Session,
    appointment_id: int,
    doctor: DoctorProfile,
) -> Appointment:
    """Fetch appointment and enforce doctor ownership. Raises 404/403."""
    appt: Appointment | None = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment id={appointment_id} not found",
        )
    if appt.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access clinical notes for your own patients",
        )
    return appt


def _require_in_consultation(appt: Appointment) -> None:
    """Business guard: appointment must be IN_CONSULTATION for note operations."""
    current = appt.status.value if hasattr(appt.status, "value") else str(appt.status)
    if current != AppointmentStatus.in_consultation.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Clinical note operations require appointment status 'in_consultation'. "
                f"Current status: '{current}'"
            ),
        )


def _note_out(note: ClinicalNote) -> ClinicalNoteOut:
    return ClinicalNoteOut(
        id=note.id,
        appointment_id=note.appointment_id,
        shorthand_input=note.shorthand_input,
        ai_draft_json=note.ai_draft_json,
        final_chief_complaint=note.final_chief_complaint,
        final_assessment=note.final_assessment,
        final_suggested_rx=note.final_suggested_rx,
        finalized_by_doctor_id=note.finalized_by_doctor_id,
        finalized_at=note.finalized_at,
    )


# ── Draft endpoint ─────────────────────────────────────────────────────────────

@router.post(
    "/appointments/{appointment_id}/clinical-note/draft",
    response_model=AIDraftOut,
    responses={
        502: {"description": "AI draft unavailable — shorthand persisted, manual entry required"},
    },
)
def create_draft(
    appointment_id: int,
    body: DraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
) -> Any:
    """FR-DOC-03 / FR-DOC-04: Doctor submits shorthand → AI returns a structured draft.

    On AI failure (timeout, API error, or malformed JSON after one retry):
      - shorthand_input is always persisted so the doctor's input is not lost.
      - ai_draft_json is left null.
      - HTTP 502 is returned with a descriptive error body.
      - The frontend should fall back to manual entry (FR-DOC-07).

    Contract choice: 502 on AI failure (not 200-with-flag) so the success
    path (200 + AIDraftOut) is unambiguous and the frontend's error branch
    is triggered by the HTTP status code, not an inspected flag.
    """
    doctor = _resolve_doctor(db, current_user)
    appt = _get_appointment_with_ownership(db, appointment_id, doctor)
    _require_in_consultation(appt)

    # Upsert: find an existing ClinicalNote or create a new one.
    # The unique constraint on clinical_notes.appointment_id ensures at most
    # one note per appointment — a duplicate INSERT would raise IntegrityError.
    note: ClinicalNote | None = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.appointment_id == appt.id)
        .first()
    )
    if note is None:
        note = ClinicalNote(appointment_id=appt.id)
        db.add(note)

    note.shorthand_input = body.shorthand_input
    db.flush()  # persist shorthand BEFORE the AI call so it's never lost

    try:
        draft: AIDraftOut = generate_clinical_draft(body.shorthand_input)
        note.ai_draft_json = draft.model_dump()
        db.commit()
        return draft

    except AIDraftGenerationError as exc:
        # Persist the shorthand even without a draft; ai_draft_json stays null.
        db.commit()
        logger.warning(
            "AI draft failed for appointment_id=%s cause=%s: %s",
            appointment_id,
            exc.cause_type,
            exc.message,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "AI draft unavailable — please enter the note manually",
                "cause": exc.cause_type,
                "shorthand_saved": True,
            },
        ) from exc


# ── Finalize endpoint ──────────────────────────────────────────────────────────

@router.post(
    "/appointments/{appointment_id}/clinical-note/finalize",
    response_model=ClinicalNoteOut,
)
def finalize_note(
    appointment_id: int,
    body: FinalizeNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
) -> Any:
    """FR-DOC-05: Doctor finalizes the clinical note for this appointment.

    THIS IS THE ONLY ENDPOINT IN THE CODEBASE PERMITTED TO WRITE:
      - clinical_notes.final_chief_complaint
      - clinical_notes.final_assessment
      - clinical_notes.final_suggested_rx
      - clinical_notes.finalized_by_doctor_id
      - clinical_notes.finalized_at

    The doctor may submit the AI draft verbatim, an edited version, or
    hand-typed content with no AI draft ever generated — all three paths
    converge identically here. This is the concrete implementation of
    "AI drafts, doctor decides."
    """
    doctor = _resolve_doctor(db, current_user)
    appt = _get_appointment_with_ownership(db, appointment_id, doctor)
    _require_in_consultation(appt)

    # Upsert — the doctor can finalize without ever having called /draft first
    note: ClinicalNote | None = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.appointment_id == appt.id)
        .first()
    )
    if note is None:
        note = ClinicalNote(appointment_id=appt.id)
        db.add(note)

    # ── THE ONLY PERMITTED WRITES TO final_ COLUMNS ───────────────────────────
    note.final_chief_complaint = body.final_chief_complaint
    note.final_assessment = body.final_assessment
    note.final_suggested_rx = body.final_suggested_rx
    note.finalized_by_doctor_id = doctor.id
    note.finalized_at = datetime.now(tz=timezone.utc)
    # ─────────────────────────────────────────────────────────────────────────

    db.commit()
    db.refresh(note)
    return _note_out(note)


# ── Complete visit endpoint ────────────────────────────────────────────────────

@router.post(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentOut,
)
def complete_visit(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
) -> Any:
    """FR-DOC-06: Doctor marks the visit as completed.

    Guards:
      1. Appointment must be owned by the calling doctor.
      2. A ClinicalNote must exist AND be finalized (finalized_at != null).
         This prevents completing a visit with only a draft or no note at all.

    Delegates the actual status transition to transition_appointment() from
    Module 4 — no transition logic is duplicated here.
    """
    doctor = _resolve_doctor(db, current_user)
    appt = _get_appointment_with_ownership(db, appointment_id, doctor)

    # Guard: clinical note must be finalized
    note: ClinicalNote | None = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.appointment_id == appt.id)
        .first()
    )
    if note is None or note.finalized_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot complete visit: clinical note has not been finalized",
        )

    # Delegate transition to Module 4's centralized guard
    completed_appt = transition_appointment(
        db, appointment_id, AppointmentStatus.completed, actor=current_user
    )
    slot = db.get(AppointmentSlot, completed_appt.slot_id)
    return _appointment_out(completed_appt, slot)
