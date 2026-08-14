"""

POST /auth/register   — create patient or doctor account
POST /auth/login      — email + password → JWT token
GET  /auth/me         — current user profile
PATCH /auth/me        — update name / phone
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserOut, TokenOut, UserUpdate
from app.services.auth import hash_password, verify_password, create_access_token
from app.config import get_settings
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()

@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    role = "patient"
    if payload.doctor_access_code:
        if payload.doctor_access_code != settings.DOCTOR_ACCESS_CODE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid doctor access code")
        role = "doctor"
    elif payload.pharmacy_access_code:
        if payload.pharmacy_access_code != settings.PHARMACY_ACCESS_CODE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid pharmacy access code")
        role = "pharmacist"

    user = User(
        name=payload.name, email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role, phone=payload.phone,
        hospital=payload.hospital or "HAMAT Hospital",
    )
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token(user.id, extra={"role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.post("/login", response_model=TokenOut)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token(user.id, extra={"role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}




@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.phone is not None:
        current_user.phone = payload.phone
    if "doctor_id" in payload.model_fields_set:
        if payload.doctor_id:
            doc = db.query(User).filter(
                User.id == payload.doctor_id, User.role == "doctor"
            ).first()
            if not doc:
                raise HTTPException(status_code=404, detail="Doctor not found")
        current_user.doctor_id = payload.doctor_id
    if payload.specialty is not None:
        current_user.specialty = payload.specialty
    if payload.hospital is not None:
        current_user.hospital = payload.hospital
    db.commit()
    db.refresh(current_user)
    return current_user