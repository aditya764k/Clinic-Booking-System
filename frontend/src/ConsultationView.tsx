import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { AlertCircle, Loader2, FileText, CheckCircle2 } from 'lucide-react'

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
  const [isDraft, setIsDraft] = useState(false)
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
          `Note saved, but could not complete visit: ${detailStr}. You can retry completion below.`
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
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-4 border-b">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Consultation</h2>
          <p className="text-slate-500">Document the clinical visit</p>
        </div>
        <div className="bg-primary/10 text-primary border border-primary/20 px-3 py-1 rounded-full text-sm font-semibold">
          Appointment #{appointmentId}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        
        {/* Shorthand Column */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Doctor's Shorthand
              </CardTitle>
              <CardDescription>
                Enter your shorthand notes to generate an AI draft.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="e.g. fever 3d, dry cough, temp 38.5C, lungs clear"
                value={shorthand}
                onChange={(e: any) => setShorthand(e.target.value)}
                className="min-h-[150px] font-mono text-sm resize-none bg-slate-50"
                disabled={loading === 'draft'}
              />
            </CardContent>
            <CardFooter>
              <Button 
                onClick={handleGenerateDraft}
                disabled={!shorthand.trim() || loading !== null}
                className="w-full"
              >
                {loading === 'draft' ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating Draft...</>
                ) : (
                  '✨ Generate AI Draft'
                )}
              </Button>
            </CardFooter>
          </Card>

          {aiError && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-md p-4 text-sm flex items-start gap-3">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5 text-amber-600" />
              <p>{aiError}</p>
            </div>
          )}
        </div>

        {/* Note Fields Column */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="text-base font-semibold">Clinical Note</CardTitle>
                <CardDescription>Review and finalize the record</CardDescription>
              </div>
              {isDraft && (
                <div className="bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 shadow-sm">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                  </span>
                  AI Draft
                </div>
              )}
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="chief-complaint">Chief Complaint</Label>
                <Textarea
                  id="chief-complaint"
                  placeholder="Primary presenting complaint..."
                  value={fields.chief_complaint}
                  onChange={(e: any) => setFields(f => ({ ...f, chief_complaint: e.target.value }))}
                  className="min-h-[80px]"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="assessment">Assessment</Label>
                <Textarea
                  id="assessment"
                  placeholder="Clinical assessment..."
                  value={fields.assessment}
                  onChange={(e: any) => setFields(f => ({ ...f, assessment: e.target.value }))}
                  className="min-h-[100px]"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="suggested-rx">Suggested Rx / Treatment</Label>
                <Textarea
                  id="suggested-rx"
                  placeholder="Treatment plan, prescriptions..."
                  value={fields.suggested_rx}
                  onChange={(e: any) => setFields(f => ({ ...f, suggested_rx: e.target.value }))}
                  className="min-h-[80px]"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-50/50">
            <CardContent className="p-6">
              {finalizeError && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-md p-4 text-sm flex flex-col gap-3 mb-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                    <p>{finalizeError}</p>
                  </div>
                  {noteFinalized && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRetryComplete}
                      disabled={loading !== null}
                      className="self-start ml-8 border-destructive text-destructive hover:bg-destructive/10"
                    >
                      Retry Completion
                    </Button>
                  )}
                </div>
              )}

              {!noteFinalized && (
                <Button
                  onClick={handleFinalizeAndComplete}
                  disabled={loading !== null}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-6 text-base"
                >
                  {loading === 'saving' ? (
                    <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Saving Note & Completing...</>
                  ) : (
                    <><CheckCircle2 className="mr-2 h-5 w-5" /> Confirm & Complete Visit</>
                  )}
                </Button>
              )}
              
              <p className="text-xs text-slate-500 text-center mt-4">
                By confirming, you take clinical responsibility for this note. <br className="hidden sm:block" />
                The AI draft (if used) is a documentation aid only.
              </p>
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  )
}
