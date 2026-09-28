/**
 * PaymentSelectorModal — Module 6: Billing & Payments
 *
 * A shadcn/ui Dialog modal that offers two payment paths:
 *  - Razorpay: creates an order via the backend, launches the Razorpay
 *    Checkout JS widget, and notifies the parent on success.
 *  - Cash: renders an amount_received form, submits to the cash endpoint,
 *    and notifies the parent on success.
 *
 * Design: "Light Mode Medical" — slate/zinc neutrals, teal primary,
 * high-contrast sans-serif. No full-page reloads on any path.
 *
 * Props:
 *   invoiceId    — the Invoice row's PK
 *   invoiceAmount — human-readable amount e.g. 500.00
 *   onSuccess    — callback when payment is confirmed (to refresh parent UI)
 *   onClose      — callback to close the modal from outside
 *   open         — controlled open state
 */
import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertCircle, CheckCircle2, Loader2, CreditCard, Banknote } from 'lucide-react'

// Declare Razorpay global loaded via CDN script tag
declare global {
  interface Window {
    Razorpay: any
  }
}

type ModalState =
  | 'idle'
  | 'razorpay_loading'
  | 'cash_form'
  | 'cash_submitting'
  | 'success'

interface Props {
  open: boolean
  invoiceId: number
  invoiceAmount: number
  razorpayKeyId?: string
  onSuccess: () => void
  onClose: () => void
}

const API = 'http://localhost:8000'

export default function PaymentSelectorModal({
  open,
  invoiceId,
  invoiceAmount,
  razorpayKeyId = '',
  onSuccess,
  onClose,
}: Props) {
  const [state, setState] = useState<ModalState>('idle')
  const [cashAmount, setCashAmount] = useState(invoiceAmount.toString())
  const [error, setError] = useState<string | null>(null)

  const handleClose = () => {
    setState('idle')
    setError(null)
    onClose()
  }

  // ── Razorpay Path ──────────────────────────────────────────────────────────

  const handleRazorpay = async () => {
    setState('razorpay_loading')
    setError(null)

    try {
      // Step 1: Create order via backend
      const resp = await fetch(`${API}/invoices/${invoiceId}/razorpay-order`, {
        method: 'POST',
        credentials: 'include',
      })

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        const detail = typeof body?.detail === 'string' ? body.detail : 'Failed to create Razorpay order.'
        setError(detail)
        setState('idle')
        return
      }

      const { order_id, amount, currency } = await resp.json()

      // Step 2: Load Razorpay script if not already present
      if (!window.Razorpay) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement('script')
          script.src = 'https://checkout.razorpay.com/v1/checkout.js'
          script.onload = () => resolve()
          script.onerror = () => reject(new Error('Failed to load Razorpay checkout script'))
          document.body.appendChild(script)
        })
      }

      // Step 3: Open Razorpay Checkout widget
      const rzp = new window.Razorpay({
        key: razorpayKeyId,
        amount,
        currency,
        order_id,
        name: 'Clinic Manager',
        description: `Invoice #${invoiceId}`,
        theme: { color: '#0d9488' }, // teal-600 to match Medical theme
        handler: (_response: any) => {
          // Payment captured on client side — webhook asynchronously finalises truth.
          // Optimistically update UI to "Paid".
          setState('success')
          setTimeout(() => {
            onSuccess()
            handleClose()
          }, 1800)
        },
        modal: {
          ondismiss: () => {
            setState('idle')
          },
        },
      })
      rzp.open()
    } catch (err: any) {
      setError(err?.message ?? 'An unexpected error occurred.')
      setState('idle')
    }
  }

  // ── Cash Path ──────────────────────────────────────────────────────────────

  const handleCashSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const amount = parseFloat(cashAmount)

    if (isNaN(amount) || amount <= 0) {
      setError('Please enter a valid positive amount.')
      return
    }
    if (amount < invoiceAmount) {
      setError(`Amount received (₹${amount}) must be at least ₹${invoiceAmount}.`)
      return
    }

    setState('cash_submitting')
    setError(null)

    try {
      const resp = await fetch(`${API}/invoices/${invoiceId}/pay-cash`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount_received: amount }),
      })

      if (resp.ok) {
        setState('success')
        setTimeout(() => {
          onSuccess()
          handleClose()
        }, 1800)
      } else {
        const body = await resp.json().catch(() => ({}))
        const detail = typeof body?.detail === 'string' ? body.detail : 'Failed to record cash payment.'
        setError(detail)
        setState('cash_form')
      }
    } catch {
      setError('Network error — could not reach the server.')
      setState('cash_form')
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) handleClose() }}>
      <DialogContent className="sm:max-w-md bg-white border border-slate-200 shadow-xl rounded-xl">
        <DialogHeader>
          <DialogTitle className="text-slate-900 text-xl font-bold">
            Collect Payment
          </DialogTitle>
          <DialogDescription className="text-slate-500">
            Invoice #{invoiceId} — Total due:{' '}
            <span className="font-semibold text-slate-800">₹{invoiceAmount.toFixed(2)}</span>
          </DialogDescription>
        </DialogHeader>

        {/* ── Success State ── */}
        {state === 'success' && (
          <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
              <CheckCircle2 className="w-9 h-9 text-emerald-600" />
            </div>
            <p className="text-lg font-semibold text-emerald-700">Payment Confirmed!</p>
            <p className="text-sm text-slate-500">Invoice #{invoiceId} is now marked as Paid.</p>
          </div>
        )}

        {/* ── Idle: Choice Screen ── */}
        {state === 'idle' && (
          <div className="flex flex-col gap-4 pt-2">
            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <button
              onClick={handleRazorpay}
              className="flex items-center gap-4 p-4 border-2 border-slate-200 rounded-xl hover:border-primary hover:bg-primary/5 transition-all text-left group"
            >
              <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center shrink-0 group-hover:bg-indigo-200 transition-colors">
                <CreditCard className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <p className="font-semibold text-slate-900">Pay via Razorpay</p>
                <p className="text-sm text-slate-500">UPI, Card, Netbanking, Wallets</p>
              </div>
            </button>

            <button
              onClick={() => { setState('cash_form'); setError(null) }}
              className="flex items-center gap-4 p-4 border-2 border-slate-200 rounded-xl hover:border-primary hover:bg-primary/5 transition-all text-left group"
            >
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center shrink-0 group-hover:bg-emerald-200 transition-colors">
                <Banknote className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <p className="font-semibold text-slate-900">Pay via Cash</p>
                <p className="text-sm text-slate-500">Record a cash collection</p>
              </div>
            </button>

            <Button variant="ghost" size="sm" onClick={handleClose} className="text-slate-400 hover:text-slate-600">
              Cancel
            </Button>
          </div>
        )}

        {/* ── Razorpay Loading ── */}
        {state === 'razorpay_loading' && (
          <div className="flex flex-col items-center justify-center py-10 gap-3 text-slate-600">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-sm">Opening Razorpay Checkout…</p>
          </div>
        )}

        {/* ── Cash Form ── */}
        {(state === 'cash_form' || state === 'cash_submitting') && (
          <form onSubmit={handleCashSubmit} className="flex flex-col gap-5 pt-2">
            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="cash-amount" className="text-slate-700 font-medium">
                Amount Received (₹)
              </Label>
              <Input
                id="cash-amount"
                type="number"
                step="0.01"
                min={invoiceAmount}
                value={cashAmount}
                onChange={(e: any) => setCashAmount(e.target.value)}
                placeholder={invoiceAmount.toString()}
                disabled={state === 'cash_submitting'}
                className="text-lg font-semibold"
              />
              <p className="text-xs text-slate-400">
                Minimum payable: ₹{invoiceAmount.toFixed(2)}
              </p>
            </div>

            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setState('idle')}
                disabled={state === 'cash_submitting'}
                className="flex-1"
              >
                Back
              </Button>
              <Button
                type="submit"
                disabled={state === 'cash_submitting'}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {state === 'cash_submitting' ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Recording…</>
                ) : (
                  'Confirm Cash Payment'
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
