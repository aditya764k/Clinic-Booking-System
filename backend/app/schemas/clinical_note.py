"""
Pydantic schemas for Module 5: Doctor Console & AI-Assisted Clinical Notes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator


class DraftRequest(BaseModel):
    """Request body for POST /appointments/{id}/clinical-note/draft."""

    shorthand_input: str

    @field_validator("shorthand_input")
    @classmethod
    def not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError(
                "shorthand_input must not be empty or whitespace-only"
            )
        return stripped


class AIDraftOut(BaseModel):
    """The structured draft returned by the Gemini service.

    Matches the JSON shape the prompt instructs the model to produce:
    {"chief_complaint": "...", "assessment": "...", "suggested_rx": "..."}
    """

    chief_complaint: str
    assessment: str
    suggested_rx: str

    model_config = {"from_attributes": True}


class FinalizeNoteRequest(BaseModel):
    """Request body for POST /appointments/{id}/clinical-note/finalize.

    All three fields are required — the doctor must explicitly submit each
    section, whether copied verbatim from the AI draft, edited, or typed
    from scratch. This is the concrete 'AI drafts, doctor decides' boundary.
    """

    final_chief_complaint: str
    final_assessment: str
    final_suggested_rx: str


class ClinicalNoteOut(BaseModel):
    """Full clinical note row returned after draft or finalize operations."""

    id: int
    appointment_id: int
    shorthand_input: Optional[str] = None
    ai_draft_json: Optional[Dict[str, Any]] = None
    final_chief_complaint: Optional[str] = None
    final_assessment: Optional[str] = None
    final_suggested_rx: Optional[str] = None
    finalized_by_doctor_id: Optional[int] = None
    finalized_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
