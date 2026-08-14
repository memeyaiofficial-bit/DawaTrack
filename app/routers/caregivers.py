"""
app/routers/caregivers.py

GET    /caregivers        — patient gets their caregivers
POST   /caregivers        — patient adds a caregiver
DELETE /caregivers/{id}   — patient removes a caregiver
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.dependencies import get_db, require_patient
from app.models.caregiver import Caregiver
from app.models.user import User

router = APIRouter(prefix="/caregivers", tags=["Caregivers"])


class CaregiverCreate(BaseModel):
    name: str
    phone: str
    relationship: str = "caregiver"
    reminders_enabled: bool = True


class CaregiverOut(BaseModel):
    id: int
    patient_id: str
    name: str
    phone: str
    relationship: str
    reminders_enabled: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CaregiverOut])
def list_caregivers(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    return db.query(Caregiver).filter(
        Caregiver.patient_id == current_user.id
    ).all()


@router.post("", response_model=CaregiverOut, status_code=status.HTTP_201_CREATED)
def add_caregiver(
    payload: CaregiverCreate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    cg = Caregiver(
        patient_id=current_user.id,
        name=payload.name,
        phone=payload.phone,
        relationship=payload.relationship,
        reminders_enabled=payload.reminders_enabled,
    )
    db.add(cg)
    db.commit()
    db.refresh(cg)
    return cg


@router.delete("/{caregiver_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_caregiver(
    caregiver_id: int,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    cg = db.query(Caregiver).filter(
        Caregiver.id == caregiver_id,
        Caregiver.patient_id == current_user.id
    ).first()
    if not cg:
        raise HTTPException(status_code=404, detail="Caregiver not found")
    db.delete(cg)
    db.commit()