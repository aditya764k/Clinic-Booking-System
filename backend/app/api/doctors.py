from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.identity import User, UserRole, DoctorProfile
from app.core.security import hash_password
from app.schemas.auth import UserOut
from app.schemas.receptionist import DoctorOut

router = APIRouter(prefix="/doctors", tags=["doctors"])

class AddDoctorRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    specialty: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v
        
    @field_validator("full_name", "specialty")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def add_doctor(
    body: AddDoctorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor"))
):
    """Allow an existing doctor to create a new doctor account."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )
        
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.doctor
    )
    db.add(user)
    db.flush()
    
    profile = DoctorProfile(
        user_id=user.id,
        full_name=body.full_name,
        specialization=body.specialty
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    
    return UserOut(
        id=user.id,
        email=user.email,
        role="doctor",
        full_name=profile.full_name,
        created_at=user.created_at,
        profile_id=profile.id
    )

@router.get("", response_model=List[DoctorOut])
def list_doctors(
    db: Session = Depends(get_db)
):
    """Return all doctor profiles (public endpoint)."""
    doctors = db.query(DoctorProfile).order_by(DoctorProfile.full_name).all()
    return [DoctorOut.model_validate(d) for d in doctors]
