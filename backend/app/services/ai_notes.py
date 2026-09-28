"""
AI-assisted clinical note drafting service.

THIS MODULE IS A PURE FUNCTION — it never touches the database.
Persistence of shorthand_input and ai_draft_json happens in the endpoint layer
(app/api/clinical_notes.py). This separation ensures the AI call can be mocked
cleanly in tests without needing DB fixtures.

Gemini is called via raw httpx REST (not the google-generativeai SDK) so that:
  1. The timeout is fully controlled by GEMINI_TIMEOUT_SECONDS from config.
  2. Mocking in tests is a simple patch on this function's import.
  3. No async runtime is needed — FastAPI endpoints using this are sync.
"""
from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings
from app.core.exceptions import AIDraftGenerationError
from app.schemas.clinical_note import AIDraftOut

logger = logging.getLogger(__name__)

# ── Gemini REST endpoint ──────────────────────────────────────────────────────
_GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)

# ── Prompt template with two few-shot examples ────────────────────────────────
# The few-shot examples stabilise the output format and reduce the chance of
# the model wrapping the JSON in markdown fences or adding preamble text.
_PROMPT_TEMPLATE = """\
You are a clinical documentation assistant. A doctor will give you shorthand \
notes from a patient consultation. Your task is to expand them into a \
structured clinical record.

Return ONLY a JSON object — no markdown, no code fences, no explanation — \
with exactly three keys:
  "chief_complaint" : the patient's primary presenting complaint
  "assessment"      : your clinical assessment summary
  "suggested_rx"    : suggested treatment or prescription notes

Examples:

Input: "fever 3d, dry cough, no sob, temp 38.5C, lungs clear"
Output: {{"chief_complaint": "Fever for 3 days with dry cough, no shortness of breath", "assessment": "Likely viral upper respiratory tract infection. Temperature 38.5°C, lungs clear on auscultation.", "suggested_rx": "Paracetamol 500mg TDS for 3 days, adequate hydration, rest. Review if fever persists beyond 5 days."}}

Input: "BP 160/100 chronic htn, c/o headache 2d, no visual changes, meds: amlodipine 5mg"
Output: {{"chief_complaint": "Headache for 2 days in a patient with chronic hypertension", "assessment": "Hypertension poorly controlled, BP 160/100. No visual symptoms or signs of hypertensive urgency.", "suggested_rx": "Increase Amlodipine to 10mg OD. Low-salt diet reinforced. Follow-up in 1 week for BP check."}}

Now process the following doctor's shorthand:

Input: "{shorthand}"
Output:"""

_RETRY_SUFFIX = (
    " Return ONLY valid JSON with keys chief_complaint, assessment, suggested_rx."
    " No other text, no markdown."
)


def _build_payload(prompt: str) -> dict:
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 512,
        },
    }


def _parse_response(response_text: str) -> AIDraftOut:
    """Parse the model's text output into AIDraftOut.

    Strips markdown fences if the model ignores the prompt instruction,
    then validates with Pydantic.
    Raises ValueError on malformed or missing-key JSON.
    """
    text = response_text.strip()
    # Strip markdown code fences if present (defensive)
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    data = json.loads(text)  # raises json.JSONDecodeError on bad JSON
    return AIDraftOut(**data)  # raises ValidationError on missing/wrong keys


def generate_clinical_draft(shorthand_input: str) -> AIDraftOut:
    """Call the Gemini API and return a structured clinical draft.

    Args:
        shorthand_input: The doctor's shorthand notes (already validated
            as non-empty by DraftRequest schema before this is called).

    Returns:
        AIDraftOut with chief_complaint, assessment, suggested_rx.

    Raises:
        AIDraftGenerationError: On timeout, non-200 API response, or
            malformed JSON after one retry. The cause_type attribute
            distinguishes the failure mode.

    This function NEVER writes to the database.
    """
    url = _GEMINI_URL_TEMPLATE.format(
        model=settings.GEMINI_MODEL,
        api_key=settings.GEMINI_API_KEY,
    )
    prompt = _PROMPT_TEMPLATE.format(shorthand=shorthand_input)

    try:
        with httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
            resp = client.post(url, json=_build_payload(prompt))
    except httpx.TimeoutException as exc:
        logger.warning("Gemini API timed out: %s", exc)
        raise AIDraftGenerationError(
            cause_type="timeout",
            message=f"Gemini API did not respond within {settings.GEMINI_TIMEOUT_SECONDS}s",
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("Gemini HTTP error: %s", exc)
        raise AIDraftGenerationError(
            cause_type="api_error",
            message=f"Network error reaching Gemini API: {exc}",
        ) from exc

    if resp.status_code != 200:
        logger.warning(
            "Gemini returned non-200: status=%s body=%s",
            resp.status_code,
            resp.text[:200],
        )
        raise AIDraftGenerationError(
            cause_type="api_error",
            message=f"Gemini API returned HTTP {resp.status_code}",
        )

    # Extract the generated text from the response structure
    try:
        raw_text: str = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIDraftGenerationError(
            cause_type="malformed_response",
            message=f"Unexpected Gemini response shape: {exc}",
        ) from exc

    # ── Attempt 1: parse the response ─────────────────────────────────────────
    try:
        return _parse_response(raw_text)
    except (json.JSONDecodeError, ValueError, TypeError, Exception):
        logger.warning(
            "Gemini returned malformed JSON on first attempt — retrying once. "
            "Raw text: %s",
            raw_text[:300],
        )

    # ── Retry once with a stricter prompt reminder ────────────────────────────
    retry_prompt = prompt + _RETRY_SUFFIX
    try:
        with httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
            resp2 = client.post(url, json=_build_payload(retry_prompt))
    except httpx.TimeoutException as exc:
        raise AIDraftGenerationError(
            cause_type="timeout",
            message=f"Gemini API timed out on retry after {settings.GEMINI_TIMEOUT_SECONDS}s",
        ) from exc

    if resp2.status_code != 200:
        raise AIDraftGenerationError(
            cause_type="api_error",
            message=f"Gemini API returned HTTP {resp2.status_code} on retry",
        )

    try:
        raw_text2: str = resp2.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_response(raw_text2)
    except Exception as exc:
        raise AIDraftGenerationError(
            cause_type="malformed_response",
            message=(
                "Gemini returned malformed JSON on both attempts. "
                f"Last raw output: {str(exc)}"
            ),
        ) from exc
