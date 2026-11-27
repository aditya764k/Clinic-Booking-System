import re

with open("backend/app/api/billing.py", "r") as f:
    content = f.read()

download_code = """
from fastapi.responses import HTMLResponse

@router.get("/invoices/{invoice_id}/download")
def download_invoice(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient", "receptionist")),
) -> Any:
    \"\"\"Return a JSON with the URL to view the HTML invoice.\"\"\"
    invoice = _get_invoice_or_404(db, invoice_id)
    # Ensure patient can only download their own invoice
    if current_user.role == UserRole.patient:
        if not invoice.appointment or not invoice.appointment.patient or invoice.appointment.patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to download this invoice")
            
    url = f"{request.base_url}invoices/{invoice_id}/html"
    return {"url": url}

@router.get("/invoices/{invoice_id}/html")
def view_invoice_html(
    invoice_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    \"\"\"Return an HTML representation of the invoice.\"\"\"
    invoice = _get_invoice_or_404(db, invoice_id)
    
    patient_name = invoice.appointment.patient.full_name if invoice.appointment and invoice.appointment.patient else "Patient"
    doctor_name = invoice.appointment.doctor.user.full_name if invoice.appointment and invoice.appointment.doctor else "Doctor"
    
    html_content = f\"\"\"
    <html>
        <head>
            <title>Invoice #{invoice.id}</title>
            <style>
                body {{ font-family: sans-serif; padding: 40px; color: #333; }}
                .invoice-box {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0, 0, 0, 0.15); }}
                h1 {{ color: #2563eb; }}
                .details {{ margin-top: 20px; border-top: 2px solid #eee; padding-top: 20px; }}
                table {{ width: 100%; text-align: left; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 12px; border-bottom: 1px solid #eee; }}
                .total {{ font-weight: bold; font-size: 1.2em; }}
                .status-paid {{ color: #16a34a; font-weight: bold; }}
                .status-pending {{ color: #ea580c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="invoice-box">
                <h1>Trimurti Clinic</h1>
                <p><strong>Invoice #{invoice.id}</strong></p>
                <p>Date: {invoice.created_at.strftime('%Y-%m-%d')}</p>
                
                <div class="details">
                    <p><strong>Patient:</strong> {patient_name}</p>
                    <p><strong>Doctor:</strong> Dr. {doctor_name}</p>
                    <p><strong>Status:</strong> <span class="{'status-paid' if invoice.status.value == 'paid' else 'status-pending'}">{invoice.status.value.upper()}</span></p>
                    <p><strong>Payment Method:</strong> {invoice.payment_method.value.upper() if invoice.payment_method else 'N/A'}</p>
                </div>
                
                <table>
                    <tr>
                        <th>Description</th>
                        <th>Amount</th>
                    </tr>
                    <tr>
                        <td>Consultation Fee</td>
                        <td>{invoice.currency} {invoice.amount}</td>
                    </tr>
                    <tr>
                        <td class="total">Total</td>
                        <td class="total">{invoice.currency} {invoice.amount}</td>
                    </tr>
                </table>
            </div>
            <script>window.print();</script>
        </body>
    </html>
    \"\"\"
    return HTMLResponse(content=html_content)

"""

# Insert at the end of the file
content = content + "\n" + download_code

with open("backend/app/api/billing.py", "w") as f:
    f.write(content)

