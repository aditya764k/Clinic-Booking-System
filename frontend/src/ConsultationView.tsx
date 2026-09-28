import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import './ConsultationView.css'

interface DraftFields {
  chief_complaint: string
  assessment: string
  suggested_rx: string
}

const API = 'http://localhost:8000'

export default function ConsultationView() {
  const { appointmentId } = useParams<{ appointmentId: string }>()
  const navigate = useNavigate()

  const [shorthand, setShorthand] = useState('')
  const [fields, setFields] = useState<DraftFields>({
    chief_complaint: '',
    assessment: '',
    suggested_rx: '',
  })
  const [isDraft, setIsDraft] = useState(false)       // true once AI populated the fields
  const [aiError, setAiError] = useState<string | null>(null)
  const [loading, setLoading] = useState<'draft' | 'saving' | null>(null)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)
  const [noteFinalized, setNoteFinalized] = useState(false)

  const handleGenerateDraft = async () => {
    if (!shorthand.trim()) return
    setLoading('draft')
    setAiError(null)
    setIsDraft(false)

    try {
      const resp = await fetch(`${API}/appointments/${appointmentId}/clinical-note/draft`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shorthand_input: shorthand }),
      })

      if (resp.ok) {
        const data: DraftFields = await resp.json()
        setFields(data)
        setIsDraft(true)
      } else if (resp.status === 502) {
        // AI unavailable — shorthand was saved server-side; allow manual entry
        const body = await resp.json().catch(() => ({}))
        const cause = body?.detail?.cause ?? 'unknown'
        setAiError(`AI draft unavailable (${cause}) — please enter the note manually below.`)
        setFields({ chief_complaint: '', assessment: '', suggested_rx: '' })
      } else {
        const body = await resp.json().catch(() => ({}))
        const detailStr = typeof body?.detail === 'string' 
          ? body.detail 
          : JSON.stringify(body?.detail || 'Unexpected error generating draft.')
        setAiError(detailStr)
      }
    } catch {
      setAiError('Network error — could not reach the server.')
    } finally {
      setLoading(null)
    }
  }

  const handleFinalizeAndComplete = async () => {
    if (!fields.chief_complaint.trim() || !fields.assessment.trim() || !fields.suggested_rx.trim()) {
      setFinalizeError('All three note fields are required before completing the visit.')
      return
    }
    setFinalizeError(null)
    setLoading('saving')

    // Step 1: Finalize the note
    if (!noteFinalized) {
      try {
        const resp = await fetch(`${API}/appointments/${appointmentId}/clinical-note/finalize`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            final_chief_complaint: fields.chief_complaint,
            final_assessment: fields.assessment,
            final_suggested_rx: fields.suggested_rx,
          }),
        })
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}))
          const detailStr = typeof body?.detail === 'string' 
            ? body.detail 
            : JSON.stringify(body?.detail || 'Failed to save note. Please try again.')
          setFinalizeError(detailStr)
          setLoading(null)
          return
        }
        setNoteFinalized(true)
      } catch {
        setFinalizeError('Network error while saving note.')
        setLoading(null)
        return
      }
    }

    // Step 2: Complete the visit
    try {
      const resp = await fetch(`${API}/appointments/${appointmentId}/complete`, {
        method: 'POST',
        credentials: 'include',
      })
      if (resp.ok) {
        navigate('/')
      } else {
        const body = await resp.json().catch(() => ({}))
        const detailStr = typeof body?.detail === 'string' 
          ? body.detail 
          : JSON.stringify(body?.detail || 'Unknown error')
        setFinalizeError(
          `Note saved, but could not complete visit: ${detailStr}. ` +
          'You can retry completion below.'
        )
      }
    } catch {
      setFinalizeError('Note saved, but network error while completing visit. You can retry.')
    } finally {
      setLoading(null)
    }
  }

  const handleRetryComplete = async () => {
    setLoading('saving')
    setFinalizeError(null)
    try {
      const resp = await fetch(`${API}/appointments/${appointmentId}/complete`, {
        method: 'POST',
        credentials: 'include',
      })
      if (resp.ok) {
        navigate('/')
      } else {
        const body = await resp.json().catch(() => ({}))
        const detailStr = typeof body?.detail === 'string' 
          ? body.detail 
          : JSON.stringify(body?.detail || 'Unknown error')
        setFinalizeError(`Still could not complete: ${detailStr}`)
      }
    } catch {
      setFinalizeError('Network error. Please try again.')
    } finally {
      setLoading(null)
    }
  }

  return (
    <main className="consultation-root">
      <header className="consultation-header">
        <div className="header-inner">
          <span className="logo-mark">🏥</span>
          <h1>Consultation</h1>
          <span className="appt-badge">Appointment #{appointmentId}</span>
        </div>
      </header>

      <div className="consultation-body">

        {/* ── Shorthand Input ─────────────────────────────────────────── */}
        <section className="card shorthand-card">
          <h2>Doctor's Shorthand</h2>
          <p className="hint">Enter your clinical shorthand and generate an AI draft, or fill the note manually below.</p>
          <textarea
            id="shorthand-input"
            className="shorthand-textarea"
            placeholder="e.g. fever 3d, dry cough, temp 38.5C, lungs clear, no sob"
            value={shorthand}
            onChange={e => setShorthand(e.target.value)}
            rows={4}
            disabled={loading === 'draft'}
          />
          <button
            id="generate-draft-btn"
            className="btn btn-primary"
            onClick={handleGenerateDraft}
            disabled={!shorthand.trim() || loading !== null}
          >
            {loading === 'draft' ? (
              <><span className="spinner" /> Generating…</>
            ) : (
              '✨ Generate AI Draft'
            )}
          </button>

          {aiError && (
            <div className="alert alert-warning" role="alert">
              <span className="alert-icon">⚠️</span>
              {aiError}
            </div>
          )}
        </section>

        {/* ── Note Fields ─────────────────────────────────────────────── */}
        <section className="card note-card">
          <div className="note-header">
            <h2>Clinical Note</h2>
            {isDraft && (
              <span className="ai-badge">🤖 AI Draft — Review Before Confirming</span>
            )}
          </div>

          <label htmlFor="chief-complaint">Chief Complaint</label>
          <textarea
            id="chief-complaint"
            className="note-field"
            placeholder="Primary presenting complaint…"
            value={fields.chief_complaint}
            onChange={e => setFields(f => ({ ...f, chief_complaint: e.target.value }))}
            rows={3}
          />

          <label htmlFor="assessment">Assessment</label>
          <textarea
            id="assessment"
            className="note-field"
            placeholder="Clinical assessment…"
            value={fields.assessment}
            onChange={e => setFields(f => ({ ...f, assessment: e.target.value }))}
            rows={4}
          />

          <label htmlFor="suggested-rx">Suggested Rx / Treatment</label>
          <textarea
            id="suggested-rx"
            className="note-field"
            placeholder="Treatment plan, prescriptions…"
            value={fields.suggested_rx}
            onChange={e => setFields(f => ({ ...f, suggested_rx: e.target.value }))}
            rows={3}
          />
        </section>

        {/* ── Confirm & Complete ──────────────────────────────────────── */}
        <section className="card action-card">
          {finalizeError && (
            <div className="alert alert-error" role="alert">
              <span className="alert-icon">❌</span>
              {finalizeError}
              {noteFinalized && (
                <button
                  className="btn btn-secondary retry-btn"
                  onClick={handleRetryComplete}
                  disabled={loading !== null}
                >
                  Retry Complete Visit
                </button>
              )}
            </div>
          )}

          {!noteFinalized && (
            <button
              id="confirm-complete-btn"
              className="btn btn-success"
              onClick={handleFinalizeAndComplete}
              disabled={loading !== null}
            >
              {loading === 'saving' ? (
                <><span className="spinner" /> Saving…</>
              ) : (
                '✅ Confirm & Complete Visit'
              )}
            </button>
          )}

          <p className="disclaimer">
            By confirming, you take clinical responsibility for this note. The AI draft (if used) is a documentation aid only.
          </p>
        </section>
      </div>
    </main>
  )
}
