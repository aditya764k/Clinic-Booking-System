from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.billing import Invoice, WebhookEvent
from app.models.appointment import Appointment
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("--- INVOICES ---")
for inv in db.query(Invoice).all():
    print(f"ID: {inv.id}, ApptID: {inv.appointment_id}, Amount: {inv.amount}, Status: {inv.status.value if hasattr(inv.status, 'value') else inv.status}, Method: {inv.payment_method}, RzpOrderID: {inv.razorpay_order_id}")

print("\n--- WEBHOOKS ---")
for wh in db.query(WebhookEvent).all():
    print(f"ID: {wh.id}, Event: {wh.razorpay_event_id}, Valid: {wh.signature_valid}")

print("\n--- APPOINTMENTS ---")
for appt in db.query(Appointment).all():
    print(f"ID: {appt.id}, Status: {appt.status.value if hasattr(appt.status, 'value') else appt.status}")

