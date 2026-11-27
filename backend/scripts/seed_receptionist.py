import os
import sys
from pathlib import Path

# Add backend dir to sys.path so we can import from app
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.core.database import SessionLocal
from app.models.identity import User, UserRole
from app.core.security import hash_password

def seed_receptionist():
    db = SessionLocal()
    try:
        # Find all receptionists
        receptionists = db.query(User).filter(User.role == UserRole.receptionist).all()
        
        target_email = "receptionist@gmail.com"
        target_password = hash_password("receptionist123")
        
        if not receptionists:
            print("No receptionist found. Creating default receptionist account.")
            new_rec = User(
                email=target_email,
                hashed_password=target_password,
                role=UserRole.receptionist
            )
            db.add(new_rec)
        else:
            print(f"Found {len(receptionists)} existing receptionist(s).")
            # We can't delete them if they have audit logs (foreign key constraints),
            # so we just scramble their emails to effectively disable them.
            if len(receptionists) > 1:
                for i, extra in enumerate(receptionists[1:]):
                    # Make sure we don't accidentally scramble the target email
                    if extra.email == target_email:
                        continue
                    extra.email = f"disabled_staff_{i}@trimurti.clinic"
                    extra.hashed_password = hash_password("disabled_account")
                    print(f"Disabled extra receptionist ID {extra.id}")
            db.flush()
            
            # Find the one that actually matches the target, or pick the first one
            primary = next((r for r in receptionists if r.email == target_email), receptionists[0])
            primary.email = target_email
            primary.hashed_password = target_password
            print(f"Updated primary receptionist to {target_email}.")
                    
        db.commit()
        print("Default receptionist seeding completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_receptionist()
