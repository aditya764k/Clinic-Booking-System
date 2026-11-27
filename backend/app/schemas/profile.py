from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    specialization: Optional[str] = None
    consultation_fee: Optional[float] = None

class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class UserProfileOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    specialization: Optional[str] = None
    consultation_fee: Optional[float] = None
    has_password: bool

    model_config = {"from_attributes": True}
