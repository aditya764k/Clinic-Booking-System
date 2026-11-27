import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.identity import DoctorProfile, User

def run():
    db = SessionLocal()
    try:
        doctors = db.query(DoctorProfile).all()
        for d in doctors:
            if "Default" in d.full_name:
                print(f"Deleting doctor: {d.full_name}")
                user = db.get(User, d.user_id)
                db.delete(d)
                if user:
                    db.delete(user)
        db.commit()
        print("Done.")
    finally:
        db.close()

if __name__ == "__main__":
    run()
