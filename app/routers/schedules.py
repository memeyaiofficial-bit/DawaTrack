"""
app/routers/schedules.py

GET/POST /schedules       — patient's own schedules
PATCH    /schedules/{id}  — toggle active/inactive
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_patient
from app.models.schedule import MedicationSchedule
from app.models.user import User
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleOut

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", response_model=list[ScheduleOut])
def list_schedules(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    return db.query(MedicationSchedule).filter(
        MedicationSchedule.patient_id == current_user.id
    ).order_by(MedicationSchedule.created_at.desc()).all()


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    sch = MedicationSchedule(patient_id=current_user.id, **payload.model_dump())
    db.add(sch)
    db.commit()
    db.refresh(sch)
    return sch


@router.patch("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    sch = db.query(MedicationSchedule).filter(
        MedicationSchedule.id == schedule_id,
        MedicationSchedule.patient_id == current_user.id,
    ).first()
    if not sch:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if payload.active is not None:
        sch.active = payload.active
    db.commit()
    db.refresh(sch)
    return sch