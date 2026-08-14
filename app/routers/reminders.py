"""

GET    /reminders/me          — patient gets their reminder schedule
POST   /reminders/me          — patient creates/replaces their reminder schedule
PATCH  /reminders/me          — patient updates time or on/off
DELETE /reminders/me          — patient disables reminders
POST   /reminders/send-now    — patient triggers an immediate test SMS to themselves
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_patient
from app.models.reminder import ReminderSchedule
from app.models.user import User
from app.schemas.reminder import (
    ReminderScheduleCreate, ReminderScheduleOut, ReminderScheduleUpdate
)
from app.services.sms import send_sms, reminder_message
from app.models.medication_log import MedicationLog
router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/me", response_model=ReminderScheduleOut | None)
def get_my_reminder(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    schedule = db.query(ReminderSchedule).filter(
        ReminderSchedule.patient_id == current_user.id
    ).first()
    return schedule  # None is fine — frontend can show "not configured"


@router.post("/me", response_model=ReminderScheduleOut, status_code=status.HTTP_201_CREATED)
def create_or_replace_reminder(
    payload: ReminderScheduleCreate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    # Upsert
    schedule = db.query(ReminderSchedule).filter(
        ReminderSchedule.patient_id == current_user.id
    ).first()
    if schedule:
        schedule.reminder_time = payload.reminder_time
        schedule.is_active = True
    else:
        schedule = ReminderSchedule(
            patient_id=current_user.id,
            reminder_time=payload.reminder_time,
        )
        db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.patch("/me", response_model=ReminderScheduleOut)
def update_reminder(
    payload: ReminderScheduleUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    schedule = db.query(ReminderSchedule).filter(
        ReminderSchedule.patient_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="No reminder schedule found — POST /reminders/me first")

    if payload.reminder_time is not None:
        schedule.reminder_time = payload.reminder_time
    if payload.is_active is not None:
        schedule.is_active = payload.is_active

    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    schedule = db.query(ReminderSchedule).filter(
        ReminderSchedule.patient_id == current_user.id
    ).first()
    if schedule:
        db.delete(schedule)
        db.commit()


@router.post("/send-now")
async def send_test_sms(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """
    Sends SMS reminders to all caregivers registered for this patient.
    Also sends to the patient themselves if they have a phone number.
    """
    from app.models.caregiver import Caregiver

    sent_to = []
    failed  = []

    # Get all caregivers with reminders enabled
    caregivers = db.query(Caregiver).filter(
        Caregiver.patient_id == current_user.id,
        Caregiver.reminders_enabled.is_(True)
    ).all()

    if not caregivers and not current_user.phone:
        raise HTTPException(
            status_code=422,
            detail="No caregivers added and no phone number on your account.",
        )

    # Send to each caregiver
    for cg in caregivers:
        msg = (
            f"Hi {cg.name}, this is a DawaTrack reminder on behalf of "
            f"{current_user.name}. Please remind them to take their medication today. "
            f"Log at dawatrack.com 💊"
        )
        ok = await send_sms(cg.phone, msg)
        if ok:
            sent_to.append(cg.name)
        else:
            failed.append(cg.name)

    # Also send to patient themselves if they have a phone
    if current_user.phone:
        latest_log = (
            db.query(MedicationLog)
            .filter(MedicationLog.patient_id == current_user.id)
            .order_by(MedicationLog.logged_at.desc())
            .first()
        )
        medicine = latest_log.medicine_name if latest_log else None
        msg = reminder_message(current_user.name, medicine)
        ok  = await send_sms(current_user.phone, msg)
        if ok:
            sent_to.append(current_user.name + " (you)")
        else:
            failed.append(current_user.name + " (you)")

    return {
        "sent_to": sent_to,
        "failed": failed,
        "detail": f"SMS sent to {len(sent_to)} recipient(s)."
    }