import sys
from pathlib import Path
sys.path.append(str(Path('/app').resolve()))
from app.core.database import SessionLocal
from app.models.identity import DoctorProfile, User

db = SessionLocal()
doctors = db.query(DoctorProfile).all()
for d in doctors:
    print(f"ID: {d.id}, User ID: {d.user_id}, Name: {d.full_name}")
