# Module 5: Doctor Console & AI-Assisted Clinical Notes

## Background (from graphify-out scan)

**What's already built and confirmed:**

| Layer | Key facts |
|---|---|
| **Model** | `ClinicalNote` at `app/models/appointment.py:63` — columns: `id`, `appointment_id (unique FK)`, `shorthand_input`, `ai_draft_json (JSON)`, `final_chief_complaint`, `final_assessment`, `final_suggested_rx`, `finalized_by_doctor_id (FK→doctor_profiles)`, `finalized_at`. Relationship `Appointment.clinical_note` (uselist=False) is already wired. |
| **State machine** | `transition_appointment()` at `app/services/appointment_state.py:70` — `IN_CONSULTATION → COMPLETED` is already in `LEGAL_TRANSITIONS` (line 44-46). |
| **RBAC** | `require_role("doctor")` factory at `app/core/dependencies.py:80`. Ownership pattern confirmed from `start_consultation()` in `app/api/appointment_state.py:275-297`. |
| **Config** | `GEMINI_API_KEY` already in `app/core/config.py:34`. `GEMINI_MODEL` and `GEMINI_TIMEOUT_SECONDS` are missing — must be added. |
| **HTTP client** | `httpx==0.27.2` is in requirements. **Use raw httpx REST call to Gemini API** (not the `google-generativeai` SDK) — gives full timeout control and matches existing httpx usage in the project. SDK is installed but REST is simpler to mock. |
| **Schemas** | Existing pattern: `model_config = {"from_attributes": True}` in Pydantic models. Flat response shapes, no nested dicts returned raw. |
| **Tests** | `conftest.py` pattern confirmed: `client` fixture + `register_user(client, role, suffix)` helper from Module 4. `os.environ["GEMINI_API_KEY"] = "test"` must be pre-set in conftest (already `os.environ` block at top). |
| **Frontend** | Plain Vite/React scaffold — no router, no auth context yet. We add `react-router-dom` and build the `ConsultationView` as the first real frontend route. |

---

## Decision: Task 4d Contract — `502` on AI failure

**Choice: Return HTTP `502 Bad Gateway` when `generate_clinical_draft()` raises `AIDraftGenerationError`.**

- The `shorthand_input` is always persisted before the AI call, so nothing is lost.
- The response on failure: `{"detail": "AI draft unavailable — <cause>", "shorthand_saved": true}`.
- The frontend handles 502 specifically: shows an inline warning and leaves the three note fields blank but editable.
- This keeps the success path (200 + `AIDraftOut`) clean and unambiguous — no `{"ai_available": false}` flag to check.

---

## Open Questions

> [!IMPORTANT]
> **Gemini model name**: The current stable model for text generation via REST API is `gemini-1.5-flash`. The plan uses this. If you have a preference (e.g. `gemini-1.5-pro` for better quality, or `gemini-2.0-flash` if you have access), let me know before execution — it's a single config value.

> [!NOTE]
> **Frontend scope**: The frontend is currently a plain Vite scaffold with no routing or auth. Module 5's frontend will add `react-router-dom` and a minimal doctor-facing consultation view only. No login screen — the user navigates manually to the route (assumes backend cookies are set). This keeps scope tight per the task spec.

---

## Proposed Changes

### 1. Config

#### [MODIFY] [config.py](file:///home/aditya/Clinic_Booking_System/clinic-app/backend/app/core/config.py)
Add below the existing `GEMINI_API_KEY` line:
```python
GEMINI_API_KEY: str = ""
GEMINI_MODEL: str = "gemini-1.5-flash"
GEMINI_TIMEOUT_SECONDS: int = 12
```

#### [MODIFY] [.env](file:///home/aditya/Clinic_Booking_System/clinic-app/.env)
Add:
```
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=12
```

---

### 2. Domain Exception

#### [MODIFY] [exceptions.py](file:///home/aditya/Clinic_Booking_System/clinic-app/backend/app/core/exceptions.py)
Add `AIDraftGenerationError` class with a `cause` string attribute and a `cause_type` enum (`"timeout"` | `"api_error"` | `"malformed_response"`). Mirrors `IllegalTransitionError` pattern.

---

### 3. Schemas

#### [NEW] `backend/app/schemas/clinical_note.py`

| Schema | Fields |
|---|---|
| `DraftRequest` | `shorthand_input: str` — `@field_validator` strips whitespace, raises `ValueError` if empty |
| `AIDraftOut` | `chief_complaint: str`, `assessment: str`, `suggested_rx: str` |
| `FinalizeNoteRequest` | `final_chief_complaint: str`, `final_assessment: str`, `final_suggested_rx: str` — all required |
| `ClinicalNoteOut` | `id`, `appointment_id`, `shorthand_input`, `ai_draft_json` (nullable), `final_chief_complaint` (nullable), `final_assessment` (nullable), `final_suggested_rx` (nullable), `finalized_by_doctor_id` (nullable), `finalized_at` (nullable) |

---

### 4. Gemini Service

#### [NEW] `backend/app/services/ai_notes.py`

```
generate_clinical_draft(shorthand_input: str) -> AIDraftOut
```

**Implementation details:**
- Calls `POST https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}` via `httpx.Client` (sync — matches the sync FastAPI endpoint pattern; no `async` used in existing services).
- Prompt template with 2 few-shot examples and instruction: "Return ONLY a JSON object with keys chief_complaint, assessment, suggested_rx. No markdown, no preamble."
- **Retry once** on malformed JSON, with stricter reminder appended.
- Timeout via `httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS)`.
- Raises `AIDraftGenerationError(cause_type=...)` on: timeout, non-200 response, malformed JSON after retry.
- **Never touches the database.** Pure function: in → out.

---

### 5. New API Endpoints

#### [NEW] `backend/app/api/clinical_notes.py`

All under `router = APIRouter(tags=["clinical-notes"])`.

**Route ordering note:** Static sub-paths (`/draft`, `/finalize`) are declared before path-param routes to match Module 4's pattern.

| Method | Path | Auth | Key Logic |
|---|---|---|---|
| `POST` | `/appointments/{id}/clinical-note/draft` | `doctor` | Ownership + status==IN_CONSULTATION guard; upsert ClinicalNote; call AI; 502 on failure |
| `POST` | `/appointments/{id}/clinical-note/finalize` | `doctor` | Ownership + status==IN_CONSULTATION guard; writes final_ fields + finalized_by/at |
| `POST` | `/appointments/{id}/complete` | `doctor` | Ownership; guard finalized_at != null; calls `transition_appointment(…, COMPLETED)` |

**Ownership pattern** (identical to `start_consultation`):
```python
doctor = db.query(DoctorProfile).filter_by(user_id=current_user.id).first()
appt = db.get(Appointment, appointment_id)
if appt.doctor_id != doctor.id: raise HTTP 403
```

**Draft endpoint upsert logic:**
```python
note = db.query(ClinicalNote).filter_by(appointment_id=appt.id).first()
if note is None:
    note = ClinicalNote(appointment_id=appt.id)
    db.add(note)
note.shorthand_input = body.shorthand_input
db.flush()  # persist shorthand before AI call
try:
    draft = generate_clinical_draft(body.shorthand_input)
    note.ai_draft_json = draft.model_dump()
    db.commit()
    return draft  # 200
except AIDraftGenerationError as e:
    db.commit()  # commit the shorthand even without a draft
    raise HTTPException(502, detail=...)
```

**Finalize endpoint write guard** (code comment mirrors Module 4's pattern):
```python
# THIS IS THE ONLY ENDPOINT PERMITTED TO WRITE final_chief_complaint,
# final_assessment, final_suggested_rx, finalized_by_doctor_id, finalized_at.
```

**Complete-visit endpoint:**
```python
note = db.query(ClinicalNote).filter_by(appointment_id=appt.id).first()
if note is None or note.finalized_at is None:
    raise HTTPException(409, "Cannot complete visit: clinical note has not been finalized")
appt = transition_appointment(db, appointment_id, AppointmentStatus.completed, actor=current_user)
return _appointment_out(appt, slot)
```

#### [MODIFY] [main.py](file:///home/aditya/Clinic_Booking_System/clinic-app/backend/app/main.py)
- Import and add `app.exception_handler(AIDraftGenerationError)` → HTTP 502.
- Mount `clinical_notes_router`.

---

### 6. Tests

#### [NEW] `backend/tests/test_clinical_notes.py`

Uses `client` and `db_session` fixtures from conftest. Uses `unittest.mock.patch` to mock `app.services.ai_notes.generate_clinical_draft`.

**Add to conftest `os.environ` block:**
```python
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["GEMINI_MODEL"] = "gemini-1.5-flash"
os.environ["GEMINI_TIMEOUT_SECONDS"] = "12"
```

**Test cases (a–h as specified):**

| Test | Mock | Assert |
|---|---|---|
| a. Draft success | Returns valid `AIDraftOut` dict | 200, `ai_draft_json` persisted, `shorthand_input` saved |
| b. Draft AI timeout | Raises `AIDraftGenerationError(cause_type="timeout")` | 502 (not 500), `shorthand_input` persisted, `ai_draft_json` null |
| c. Draft malformed JSON | Raises `AIDraftGenerationError(cause_type="malformed_response")` | 502, graceful, `shorthand_input` saved |
| d1. Finalize (AI-assisted) | No AI mock needed — seeds ai_draft_json, then finalizes | 200, all final_ fields written |
| d2. Finalize (manual — no draft) | No draft ever called | 200, final_ fields written, `ai_draft_json` stays null |
| e1. Complete — no note | No ClinicalNote row | 409 |
| e2. Complete — draft only | `finalized_at` is null | 409 |
| e3. Complete — finalized | `finalized_at` set | 200, status=completed, `completed_at` set |
| f. Ownership | Wrong doctor → each endpoint | 403 |
| g. Wrong state (checked_in) | Appointment not in_consultation | 409 |
| h. Full manual path | No draft, direct finalize → complete | 200 end-to-end |

---

### 7. Frontend

#### [MODIFY] `frontend/src/App.tsx`
Wrap with `BrowserRouter` + `Routes`. Add route `/consultation/:appointmentId` → `ConsultationView`.

#### [NEW] `frontend/src/ConsultationView.tsx`

**State:**
- `shorthand: string` — textarea value
- `draft: {chief_complaint, assessment, suggested_rx} | null`
- `fields: {chief_complaint, assessment, suggested_rx}` — editable final values
- `aiError: string | null`
- `loading: "draft" | "finalize" | "complete" | null`
- `finalizeError: string | null`

**Flow:**
1. "Generate Draft" → `POST /appointments/{id}/clinical-note/draft`
   - On 200: populate `fields` from response, set `draft`, show "AI Draft — Review Before Confirming" badge.
   - On 502/any error: set `aiError`, leave `fields` empty but editable.
2. "Confirm & Complete Visit" → `POST /appointments/{id}/clinical-note/finalize` then on success → `POST /appointments/{id}/complete`, then navigate back.
   - If finalize succeeds but complete fails: show `finalizeError`, allow retry of complete only (don't re-enter note).

#### [MODIFY] `frontend/package.json`
Add `react-router-dom`.

---

## File Summary

| File | Action |
|---|---|
| `app/core/config.py` | MODIFY — add `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS` |
| `app/core/exceptions.py` | MODIFY — add `AIDraftGenerationError` |
| `app/schemas/clinical_note.py` | NEW |
| `app/services/ai_notes.py` | NEW |
| `app/api/clinical_notes.py` | NEW |
| `app/main.py` | MODIFY — mount router, add exception handler |
| `tests/conftest.py` | MODIFY — add Gemini env vars |
| `tests/test_clinical_notes.py` | NEW |
| `frontend/src/ConsultationView.tsx` | NEW |
| `frontend/src/App.tsx` | MODIFY — add routing |
| `frontend/package.json` | MODIFY — add react-router-dom |
| `.env` | MODIFY — add GEMINI_MODEL, GEMINI_TIMEOUT_SECONDS |

---

## Verification Plan

### Automated Tests
```bash
# Backend — all Module 5 tests
DATABASE_URL=sqlite:// JWT_SECRET_KEY=test-key \
  .venv/bin/pytest tests/test_clinical_notes.py -v

# Full regression (Modules 1–5)
DATABASE_URL=sqlite:// JWT_SECRET_KEY=test-key \
  .venv/bin/pytest tests/ -v
```

### Manual Verification
1. Start backend (`uvicorn app.main:app --reload`) + frontend (`npm run dev`).
2. Register a doctor, book and check-in and start-consultation on an appointment via Swagger.
3. Navigate to `http://localhost:5173/consultation/{appointment_id}`.
4. Type shorthand → click Generate Draft → verify AI fields populate.
5. Edit one field → click Confirm & Complete Visit → verify appointment status = `completed` in DB.
6. Repeat but skip Generate Draft entirely (manual path) — confirm it also completes successfully.
