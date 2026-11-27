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


class PrescriptionItem(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str] = None


class LabTestItem(BaseModel):
    test_name: str
    reason: Optional[str] = None


class AIDraftOut(BaseModel):
    """The structured draft returned by the Gemini service.

    Matches the JSON shape the prompt instructs the model to produce.
    """
    symptoms: str
    diagnosis: str
    treatment_plan: str
    prescriptions: list[PrescriptionItem]
    lab_tests_recommended: list[LabTestItem]
    follow_up_date: Optional[str] = None

    model_config = {"from_attributes": True}


class FinalizeNoteRequest(BaseModel):
    """Request body for POST /appointments/{id}/clinical-note/finalize.
    
    The doctor must explicitly submit each section.
    """
    symptoms: str
    diagnosis: str
    treatment_plan: str
    prescriptions: list[PrescriptionItem]
    lab_tests_recommended: list[LabTestItem]
    follow_up_date: Optional[str] = None
    additional_treatment_charges: Optional[float] = None
    treatment_charge_description: Optional[str] = None


class ClinicalNoteOut(BaseModel):
    """Full clinical note row returned after draft or finalize operations."""

    id: int
    appointment_id: int
    shorthand_input: Optional[str] = None
    ai_draft_json: Optional[Dict[str, Any]] = None
    
    # New structured fields
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    prescriptions: Optional[list[PrescriptionItem]] = None
    lab_tests_recommended: Optional[list[LabTestItem]] = None
    follow_up_date: Optional[datetime] = None
    additional_treatment_charges: Optional[float] = None
    treatment_charge_description: Optional[str] = None
    
    # Deprecated fields (kept for backward compatibility with old records if needed)
    final_chief_complaint: Optional[str] = None
    final_assessment: Optional[str] = None
    final_suggested_rx: Optional[str] = None
    finalized_by_doctor_id: Optional[int] = None
    finalized_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
