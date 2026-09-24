"""
scripts/verify_module1.py
=========================
Module 1 verification script — exercises the full data chain:
  patient → doctor → appointment_slot → appointment

Also verifies that the Postgres-level UNIQUE constraint on
(doctor_id, slot_start) raises an IntegrityError, not an
application-level validation error.

Run inside the backend Docker container:
    python scripts/verify_module1.py

Or from the host with the clinic-app root as cwd:
    docker exec -w /app -e DATABASE_URL=... clinic_backend python scripts/verify_module1.py
"""

import sys
import traceback
from datetime import datetime, timezone, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Make sure app.* imports resolve when running as a top-level script
import os, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, engine
from app.models.identity import User, PatientProfile, DoctorProfile, UserRole
from app.models.scheduling import AppointmentSlot
from app.models.appointment import Appointment, AppointmentStatus


def hr(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def cleanup(session) -> None:
    """Remove any rows from a prior run so the script is idempotent."""
    session.execute(text("DELETE FROM appointments"))
    session.execute(text("DELETE FROM appointment_slots"))
    session.execute(text("DELETE FROM patient_profiles"))
    session.execute(text("DELETE FROM doctor_profiles"))
    session.execute(text("DELETE FROM audit_logs"))
    session.execute(text("DELETE FROM users"))
    session.commit()
    print("[setup] Old test data cleaned up.")


def main() -> None:
    hr("MODULE 1 — DATA LAYER VERIFICATION")

    session = SessionLocal()

    # ------------------------------------------------------------------
    # 0. Clean slate
    # ------------------------------------------------------------------
    cleanup(session)

    # ------------------------------------------------------------------
    # 1. Insert one User of each role
    # ------------------------------------------------------------------
    hr("Step 1: Insert Users (patient / receptionist / doctor)")

    patient_user = User(
        email="patient@clinic.test",
        hashed_password="$2b$12$dummyhash_patient",
        role=UserRole.patient,
        created_at=datetime.now(timezone.utc),
    )
    receptionist_user = User(
        email="receptionist@clinic.test",
        hashed_password="$2b$12$dummyhash_receptionist",
        role=UserRole.receptionist,
        created_at=datetime.now(timezone.utc),
    )
    doctor_user = User(
        email="doctor@clinic.test",
        hashed_password="$2b$12$dummyhash_doctor",
        role=UserRole.doctor,
        created_at=datetime.now(timezone.utc),
    )

    session.add_all([patient_user, receptionist_user, doctor_user])
    session.flush()   # assign IDs before creating profiles

    print(f"  ✓ patient_user.id       = {patient_user.id}")
    print(f"  ✓ receptionist_user.id  = {receptionist_user.id}")
    print(f"  ✓ doctor_user.id        = {doctor_user.id}")

    # ------------------------------------------------------------------
    # 2. Insert PatientProfile and DoctorProfile
    # ------------------------------------------------------------------
    hr("Step 2: Insert PatientProfile & DoctorProfile")

    patient_profile = PatientProfile(
        user_id=patient_user.id,
        full_name="Aditya Kumar",
        phone="+91-9876543210",
        date_of_birth=datetime(1995, 6, 15).date(),
    )
    doctor_profile = DoctorProfile(
        user_id=doctor_user.id,
        full_name="Dr. Priya Sharma",
        specialization="General Medicine",
        working_hours_config={"mon": "09:00-17:00", "tue": "09:00-17:00"},
    )

    session.add_all([patient_profile, doctor_profile])
    session.flush()

    print(f"  ✓ patient_profile.id    = {patient_profile.id}  (user_id={patient_profile.user_id})")
    print(f"  ✓ doctor_profile.id     = {doctor_profile.id}   (user_id={doctor_profile.user_id})")

    # ------------------------------------------------------------------
    # 3. Insert one AppointmentSlot for the doctor
    # ------------------------------------------------------------------
    hr("Step 3: Insert AppointmentSlot")

    slot_start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    slot_end   = slot_start + timedelta(minutes=30)

    slot = AppointmentSlot(
        doctor_id=doctor_profile.id,
        slot_start=slot_start,
        slot_end=slot_end,
    )
    session.add(slot)
    session.flush()

    print(f"  ✓ slot.id               = {slot.id}")
    print(f"    doctor_id             = {slot.doctor_id}")
    print(f"    slot_start            = {slot.slot_start}")

    # ------------------------------------------------------------------
    # 4. Insert one Appointment linking patient → doctor → slot
    # ------------------------------------------------------------------
    hr("Step 4: Insert Appointment (status=booked)")

    appt = Appointment(
        patient_id=patient_profile.id,
        doctor_id=doctor_profile.id,
        slot_id=slot.id,
        status=AppointmentStatus.booked,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(appt)
    session.commit()

    print(f"  ✓ appointment.id        = {appt.id}")
    print(f"    patient_id            = {appt.patient_id}")
    print(f"    doctor_id             = {appt.doctor_id}")
    print(f"    slot_id               = {appt.slot_id}")
    print(f"    status                = {appt.status}")

    # ------------------------------------------------------------------
    # 5. Print full chain
    # ------------------------------------------------------------------
    hr("Step 5: Full Chain Summary")
    # Re-query via ORM navigation to confirm relationships resolve
    session.expire_all()
    loaded_appt = session.get(Appointment, appt.id)
    print(
        f"  Patient  → {loaded_appt.patient.full_name} (user: {loaded_appt.patient.user.email})\n"
        f"  Doctor   → {loaded_appt.doctor.full_name} (user: {loaded_appt.doctor.user.email})\n"
        f"  Slot     → {loaded_appt.slot.slot_start} – {loaded_appt.slot.slot_end}\n"
        f"  Status   → {loaded_appt.status}\n"
        f"\n  ✅ CHAIN INSERT SUCCESS: patient → doctor → slot → appointment"
    )

    # ------------------------------------------------------------------
    # 6. Duplicate slot test — MUST raise Postgres IntegrityError
    # ------------------------------------------------------------------
    hr("Step 6: Duplicate (doctor_id, slot_start) — IntegrityError Check")
    print("  Attempting to insert a slot with the SAME (doctor_id, slot_start)...")

    duplicate_ok = False
    try:
        duplicate_slot = AppointmentSlot(
            doctor_id=doctor_profile.id,  # same doctor
            slot_start=slot_start,        # same start time → DUPLICATE
            slot_end=slot_end + timedelta(minutes=30),
        )
        session.add(duplicate_slot)
        session.commit()
        print("  ✗ FAIL — No exception raised! Constraint is missing from the database.")
    except IntegrityError as exc:
        session.rollback()
        duplicate_ok = True
        print(f"  ✓ IntegrityError raised as expected:")
        # Show just the key part of the error
        detail = str(exc.orig).splitlines()[0] if exc.orig else str(exc)
        print(f"    {detail}")
        print(f"\n  ✅ PASS — Postgres UNIQUE CONSTRAINT (doctor_id, slot_start) is enforced at the DB level.")
    except Exception as exc:
        session.rollback()
        print(f"  ✗ FAIL — Unexpected exception type: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    hr("FINAL RESULT")
    chain_ok = True  # if we got here the chain insert succeeded
    print(f"  Chain insert:              {'PASS ✅' if chain_ok else 'FAIL ❌'}")
    print(f"  Duplicate-slot constraint: {'PASS ✅' if duplicate_ok else 'FAIL ❌'}")
    print()

    session.close()
    sys.exit(0 if (chain_ok and duplicate_ok) else 1)


if __name__ == "__main__":
    main()
