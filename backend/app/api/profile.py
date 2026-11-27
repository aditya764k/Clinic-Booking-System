from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import verify_password, hash_password
from app.models.identity import User, PatientProfile, DoctorProfile, UserRole
from app.schemas.profile import UpdateProfileRequest, UpdatePasswordRequest, UserProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])

def _get_profile_out(user: User, db: Session) -> UserProfileOut:
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    data = {
        "id": user.id,
        "email": user.email,
        "role": role_val,
        "has_password": user.hashed_password is not None,
    }
    
    if role_val == "patient":
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == user.id).first()
        if profile:
            data.update({
                "full_name": profile.full_name,
                "phone": profile.phone,
                "date_of_birth": profile.date_of_birth,
            })
    elif role_val == "doctor":
        profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
        if profile:
            data.update({
                "full_name": profile.full_name,
                "specialization": profile.specialization,
                "consultation_fee": profile.consultation_fee,
            })
            
    return UserProfileOut(**data)

@router.get("/me", response_model=UserProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's profile details."""
    return _get_profile_out(current_user, db)

@router.put("/me", response_model=UserProfileOut)
def update_my_profile(
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the current user's profile details."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    
    if role_val == "patient":
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        if body.full_name is not None:
            profile.full_name = body.full_name
        if body.phone is not None:
            profile.phone = body.phone
        if body.date_of_birth is not None:
            profile.date_of_birth = body.date_of_birth
            
    elif role_val == "doctor":
        profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
            
        if body.full_name is not None:
            profile.full_name = body.full_name
        if body.specialization is not None:
            profile.specialization = body.specialization
        if body.consultation_fee is not None:
            profile.consultation_fee = body.consultation_fee
    else:
        raise HTTPException(status_code=403, detail="Profile update not supported for this role")
        
    db.commit()
    return _get_profile_out(current_user, db)

@router.put("/me/password")
def update_password(
    body: UpdatePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the current user's password."""
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="User does not have a password set (e.g. Google Login)")
        
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()
    
    return {"detail": "Password updated successfully"}
