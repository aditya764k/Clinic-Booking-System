import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from app.models.appointment import Appointment, ClinicalNote

def generate_prescription_pdf(appointment: Appointment, note: ClinicalNote) -> io.BytesIO:
    """Generate a professional PDF prescription for the given appointment and clinical note."""
    buffer = io.BytesIO()
    
    # Setup document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.alignment = 1 # Center
    
    h2_style = styles["Heading2"]
    h2_style.textColor = colors.HexColor("#4f46e5")
    
    normal_style = styles["Normal"]
    normal_style.fontSize = 10
    normal_style.leading = 14
    
    elements = []
    
    # ── Header ──────────────────────────────────────────────────────────────
    elements.append(Paragraph("<b>TRIMURTI CLINIC</b>", title_style))
    elements.append(Paragraph("123 Healthcare Avenue, Medical District, City - 400001", styles["Normal"]))
    elements.append(Paragraph("Phone: +91-9876543210 | Email: contact@trimurticlinic.com", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))
    
    # ── Patient Details ─────────────────────────────────────────────────────
    patient = appointment.patient
    doctor = appointment.doctor
    
    date_str = appointment.completed_at.strftime("%B %d, %Y") if appointment.completed_at else datetime.now().strftime("%B %d, %Y")
    
    patient_info = [
        ["Patient Name:", patient.full_name, "Date:", date_str],
        ["Patient Phone:", patient.phone or "N/A", "Doctor:", f"Dr. {doctor.full_name}"]
    ]
    
    pt_table = Table(patient_info, colWidths=[1.5*inch, 2.5*inch, 1*inch, 2*inch])
    pt_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    
    elements.append(pt_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # ── Clinical Note Data ──────────────────────────────────────────────────
    if note.symptoms:
        elements.append(Paragraph("<b>Symptoms:</b>", h2_style))
        elements.append(Paragraph(note.symptoms.replace('\n', '<br/>'), normal_style))
        elements.append(Spacer(1, 0.1 * inch))
        
    if note.diagnosis:
        elements.append(Paragraph("<b>Diagnosis:</b>", h2_style))
        elements.append(Paragraph(note.diagnosis.replace('\n', '<br/>'), normal_style))
        elements.append(Spacer(1, 0.1 * inch))
        
    if note.treatment_plan:
        elements.append(Paragraph("<b>Treatment Plan:</b>", h2_style))
        elements.append(Paragraph(note.treatment_plan.replace('\n', '<br/>'), normal_style))
        elements.append(Spacer(1, 0.2 * inch))
        
    # ── Prescriptions ───────────────────────────────────────────────────────
    if note.prescriptions and len(note.prescriptions) > 0:
        elements.append(Paragraph("<b>Medicines:</b>", h2_style))
        
        rx_data = [["Medicine Name", "Dosage", "Frequency", "Duration", "Instructions"]]
        for rx in note.prescriptions:
            rx_data.append([
                rx.get("medicine_name", ""),
                rx.get("dosage", ""),
                rx.get("frequency", ""),
                rx.get("duration", ""),
                rx.get("instructions", "")
            ])
            
        rx_table = Table(rx_data, colWidths=[1.8*inch, 1*inch, 1.2*inch, 1*inch, 2*inch])
        rx_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#0f172a")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1"))
        ]))
        
        elements.append(rx_table)
        elements.append(Spacer(1, 0.2 * inch))
        
    # ── Lab Tests ───────────────────────────────────────────────────────────
    if note.lab_tests_recommended and len(note.lab_tests_recommended) > 0:
        elements.append(Paragraph("<b>Recommended Lab Tests:</b>", h2_style))
        
        lab_data = [["Test Name", "Reason"]]
        for lab in note.lab_tests_recommended:
            lab_data.append([
                lab.get("test_name", ""),
                lab.get("reason", "")
            ])
            
        lab_table = Table(lab_data, colWidths=[3*inch, 4*inch])
        lab_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#0f172a")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1"))
        ]))
        
        elements.append(lab_table)
        elements.append(Spacer(1, 0.2 * inch))
        
    # ── Footer ──────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.5 * inch))
    
    if note.follow_up_date:
        elements.append(Paragraph(f"<b>Follow-up Date:</b> {note.follow_up_date.strftime('%B %d, %Y')}", normal_style))
        
    elements.append(Spacer(1, 1 * inch))
    elements.append(Paragraph(f"Dr. {doctor.full_name}", styles["Normal"]))
    elements.append(Paragraph("Signature", styles["Normal"]))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
