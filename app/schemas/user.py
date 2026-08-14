"""
user schema
"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, validator


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    # Provide the doctor access code to register as a doctor
    doctor_access_code: str | None = None
    pharmacy_access_code: str | None = None
    hospital: str | None = None

    @validator("password")
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @validator("name")
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    phone: str | None = None
    doctor_id: str | None = None  # ← field script.js sends
    specialty: str | None = None
    hospital: str | None = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: Literal["patient", "doctor", "pharmacist"]
    phone: str | None
    is_active: bool
    created_at: datetime
    doctor_id: str | None = None
    specialty: str | None = None
    hospital: str | None = None

    class Config:
        from_orm = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut