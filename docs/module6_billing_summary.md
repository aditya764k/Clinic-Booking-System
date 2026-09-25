# Module 6: Billing & Payments — Architecture & Concepts Summary

This document summarizes the approach, logic, security principles, and core concepts implemented in Module 6 of the Clinic Appointment Manager.

## 1. Core Philosophy: The Server is the Source of Truth
The most critical rule of the billing module is **Zero Trust** regarding pricing data from the client.
- **No Client Pricing**: The frontend `PaymentSelectorModal` is never allowed to dictate how much an invoice costs. The `amount` is strictly computed on the backend using the `CONSULTATION_FEE` constant when the invoice is created.
- **Guarded State Machine**: Module 6 relies entirely on the central state machine built in Module 4 (`transition_appointment`). Billing cannot arbitrarily change appointment statuses; it must adhere to the legal transition flow: `COMPLETED` → `BILLING_PENDING` → `PAID`.

## 2. Idempotency (Safe Retries)
Payment gateways like Razorpay operate on an "at-least-once" delivery guarantee for webhooks. This means the same payment success webhook might hit our backend multiple times.

**How we solved it:**
- **WebhookEvent Table**: We created a dedicated table with a `UNIQUE` constraint on the `razorpay_event_id`. 
- **ON CONFLICT DO NOTHING**: When a webhook arrives, we immediately attempt to `INSERT` it into this table. If it's a duplicate, the database throws an `IntegrityError`, which we catch and silently return a `200 OK` to Razorpay. 
- **Result**: The system safely absorbs duplicate webhook replays without double-processing the payment, and returning `200` ensures Razorpay stops retrying.

## 3. Mutual Exclusivity (No Double Charging)
Because we offer two payment paths (Razorpay and Cash), there is a risk of a race condition where a patient pays online at the exact same moment a receptionist records a cash payment.

**How we solved it:**
- **Status Locks**: The moment a receptionist clicks "Pay via Razorpay", the backend generates an order and locks the `payment_method` to `razorpay`.
- **Cash Guard**: If a receptionist tries to collect cash on an invoice locked to Razorpay, the backend rejects it (`409 Conflict`).
- **Webhook Guard**: Conversely, if an invoice is successfully paid via cash, and a delayed Razorpay webhook arrives later, the webhook handler detects the cash payment and rejects the Razorpay event, preventing the system state from being corrupted.

## 4. Atomic Database Transactions
Financial data requires atomicity — either *everything* succeeds, or *nothing* succeeds.

**How we solved it:**
When a payment succeeds (either via Cash or Webhook), multiple things must happen:
1. `Invoice.status` changes to `paid`.
2. `Invoice.paid_at` is timestamped.
3. `AuditLog` row is created (for cash collections).
4. `Appointment.status` transitions to `PAID`.

We use `db.flush()` to stage all the invoice and audit log changes, and then we rely on `transition_appointment()` to execute the final `db.commit()`. If the server crashes anywhere in this pipeline, the entire transaction rolls back, preventing a scenario where an invoice is paid but the appointment remains pending.

## 5. Security & HMAC Verification
Razorpay webhooks are public endpoints (they cannot pass a Receptionist authentication cookie). This opens the system up to malicious actors spoofing payment confirmations.

**How we solved it:**
- **Cryptographic Signatures**: Razorpay signs every webhook payload using our secret key (`RAZORPAY_WEBHOOK_SECRET`) and a SHA-256 HMAC algorithm.
- **Constant-Time Comparison**: Our backend recalculates the signature from the raw request body and compares it to the `X-Razorpay-Signature` header. We strictly use Python's `hmac.compare_digest()` instead of standard string equality (`==`) to prevent **Timing Attacks** (where a hacker guesses the signature character-by-character based on how many milliseconds the server takes to reject it).

## 6. Frontend Degradation & UX
The `PaymentSelectorModal` is designed with robust error handling to gracefully degrade if the backend fails:
- It fetches the exact `amount` from the backend invoice before opening Razorpay, ensuring what the patient sees matches the database.
- The Cash form uses HTML5 validation `min={invoiceAmount}` but the backend acts as the ultimate enforcer (`422 Unprocessable Entity` if the cash tendered is less than the invoice amount).
- Upon Razorpay's JavaScript `handler` succeeding, the UI optimistically shows a "Success" state, but the actual source of truth is finalized asynchronously in the background via the webhook.

## Summary of DB Constraints Utilized
| Constraint | Purpose |
| :--- | :--- |
| `UNIQUE(razorpay_event_id)` | Prevents processing the same Razorpay webhook twice. |
| `FOREIGN KEY (appointment_id)` | Links the Invoice permanently to the clinical visit. |
| `CHECK (amount >= 0)` | Prevents negative invoices. |
