"""
Reusable FastAPI dependencies: DB session, current user, role guards.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.auth import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    """Yield a SQLAlchemy session and close it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_doctor(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor access only")
    return current_user


def require_patient(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient access only")
    return current_user

def require_pharmacist(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "pharmacist":
        raise HTTPException(status_code=403, detail="Pharmacist access only")
    return current_user

def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Doctors and pharmacists both count as clinical staff."""
    if current_user.role not in ("doctor", "pharmacist"):
        raise HTTPException(status_code=403, detail="Staff access only")
    return current_user