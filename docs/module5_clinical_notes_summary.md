# Module 5: Doctor Console & AI-Assisted Clinical Notes

This document summarizes the architecture, design patterns, and business logic implemented in Module 5 for managing the clinical notes and AI draft generation.

## Core Architectural Concepts

### 1. The "Pure Function" AI Service
The Gemini integration (`app/services/ai_notes.py`) is designed as a **pure function**. It takes a string (`shorthand_input`) and returns a structured Pydantic object (`AIDraftOut`), or raises an `AIDraftGenerationError`. 

**Why this matters:**
- **No Database Coupling**: The AI service knows nothing about SQLAlchemy, `appointment_ids`, or `ClinicalNote` rows. This separation of concerns makes it trivial to unit test (just mock the function) and means the AI logic can be reused in future contexts without dragging database dependencies with it.
- **Raw `httpx` over Google SDK**: We used raw REST calls via `httpx.Client` rather than Google's `google-generativeai` SDK. This gives us exact control over network timeouts (via `GEMINI_TIMEOUT_SECONDS`), aligns with the existing sync API pattern, and makes mocking in tests much simpler.
- **Few-Shot Prompting**: The prompt includes two strict "Input/Output" examples. This stabilizes the LLM's output format, drastically reducing the chances of it returning conversational text or wrapping the JSON in markdown fences.

### 2. "AI Drafts, Doctor Decides" (The Boundary)
Module 5 strictly enforces that the AI is an assistant, not an autonomous actor.

- **The Draft Endpoint**: Generates an AI suggestion and stores it in a separate JSON column (`ai_draft_json`).
- **The Finalize Endpoint**: Accepts three explicitly required string fields (`final_chief_complaint`, `final_assessment`, `final_suggested_rx`). The doctor *must* submit these. It doesn't matter if the doctor copied the AI draft verbatim, heavily edited it, or typed it from scratch without ever clicking "Generate Draft". 
- **Single-Writer Discipline**: Similar to Module 4, `POST /appointments/{id}/clinical-note/finalize` is the *only* endpoint permitted to write to the `final_...` columns and set the `finalized_by_doctor_id` / `finalized_at` audit fields.

### 3. Graceful Degradation & Error Handling
We built the system to handle AI failures gracefully so doctors are never blocked from doing their jobs.

- **Persist First, Call Second**: When the doctor clicks "Generate Draft", the system does a `db.flush()` to save their `shorthand_input` to the database *before* making the network call to Gemini. If Gemini times out, the doctor's shorthand is safely stored.
- **The 502 Contract**: If the AI generation fails (timeout, 500 error from Google, or malformed JSON that fails the retry), the domain exception `AIDraftGenerationError` is raised. The global FastAPI exception handler converts this to an HTTP `502 Bad Gateway`. 
- **Frontend Fallback**: The React frontend detects the `502` status, displays a warning banner ("AI draft unavailable"), but leaves the three clinical note text boxes editable. The doctor just types the note manually and proceeds.

### 4. Ownership & State Guards
Module 5 relies heavily on the groundwork laid in Module 4.

- **Ownership**: Every endpoint fetches the calling user's `DoctorProfile` and checks that it matches the `appointment.doctor_id`. A doctor cannot draft or finalize a note for another doctor's patient (HTTP 403 Forbidden).
- **State Guard (In Consultation)**: Notes can only be drafted or finalized if the appointment is in the `in_consultation` state (HTTP 409 Conflict).
- **State Guard (Completion)**: The `POST /appointments/{id}/complete` endpoint checks that a `ClinicalNote` exists and `finalized_at` is set before allowing the visit to complete. If valid, it delegates the actual database write to Module 4's `transition_appointment()` function.

## Testing Strategy
The test suite (`tests/test_clinical_notes.py`) achieves full coverage without making a single real network call to Gemini.

- **`unittest.mock.patch`**: We intercept `app.api.clinical_notes.generate_clinical_draft`.
- **Failure Matrix**: The tests explicitly verify what happens when the mock raises a timeout vs. malformed JSON. They verify that the endpoint returns `502` and that the `shorthand_input` is successfully found in the SQLite database afterwards.
- **The "Full Manual" Path**: Test `h` proves that the system works end-to-end (Finalize -> Complete) even if the AI draft endpoint is never called once.
