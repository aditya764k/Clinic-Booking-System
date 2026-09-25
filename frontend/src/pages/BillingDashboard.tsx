import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertCircle, Loader2 } from 'lucide-react'
import PaymentSelectorModal from '@/components/PaymentSelectorModal'

const API = 'http://localhost:8000'

export default function BillingDashboard() {
  const [appointmentId, setAppointmentId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // State for the modal
  const [modalOpen, setModalOpen] = useState(false)
  const [currentInvoice, setCurrentInvoice] = useState<{ id: number; amount: number } | null>(null)

  const handleGenerateInvoice = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!appointmentId) return

    setLoading(true)
    setError(null)

    try {
      const resp = await fetch(`${API}/appointments/${appointmentId}/invoice`, {
        method: 'POST',
        credentials: 'include',
      })

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        const detail = typeof body?.detail === 'string' ? body.detail : 'Failed to generate invoice.'
        setError(detail)
        setLoading(false)
        return
      }

      const invoice = await resp.json()
      setCurrentInvoice({ id: invoice.id, amount: invoice.amount })
      setModalOpen(true)
    } catch (err: any) {
      setError('Network error — could not reach the server.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto mt-10 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Receptionist Billing Desk</CardTitle>
          <CardDescription>Enter a completed Appointment ID to generate an invoice and collect payment.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleGenerateInvoice} className="space-y-4">
            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="appointmentId">Appointment ID</Label>
              <div className="flex gap-3">
                <Input
                  id="appointmentId"
                  value={appointmentId}
                  onChange={(e) => setAppointmentId(e.target.value)}
                  placeholder="e.g., 42"
                  disabled={loading}
                />
                <Button type="submit" disabled={loading || !appointmentId}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Generate Invoice'}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {currentInvoice && (
        <PaymentSelectorModal
          open={modalOpen}
          invoiceId={currentInvoice.id}
          invoiceAmount={currentInvoice.amount}
          razorpayKeyId="test_key"
          onSuccess={() => {
            setModalOpen(false)
            setAppointmentId('')
            alert('Payment successfully completed!')
          }}
          onClose={() => setModalOpen(false)}
        />
      )}
    </div>
  )
}
