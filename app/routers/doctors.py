"""
app/routers/doctors.py

GET /doctors — list all doctors with patient counts (for the picker)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.dependencies import get_db, get_current_user
from app.models.user import User

router = APIRouter(prefix="/doctors", tags=["Doctors"])


class DoctorOut(BaseModel):
    id: str
    name: str
    email: str
    specialty: str | None = None
    hospital: str | None = None
    patient_count: int = 0

    model_config = {"from_attributes": True}


@router.get("", response_model=list[DoctorOut])
def list_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctors = db.query(User).filter(User.role == "doctor").all()
    counts = dict(
        db.query(User.doctor_id, func.count(User.id))
        .filter(User.role == "patient", User.doctor_id.isnot(None))
        .group_by(User.doctor_id)
        .all()
    )
    result = []
    for d in doctors:
        result.append(DoctorOut(
            id=d.id, name=d.name, email=d.email,
            specialty=d.specialty, hospital=d.hospital,
            patient_count=counts.get(d.id, 0),
        ))
    return result