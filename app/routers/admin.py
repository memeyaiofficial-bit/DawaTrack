"""
Internal-only endpoints — protected by a static admin API key header.
These are NOT exposed in the public Swagger docs.

POST /admin/run-reminders   — manually fire the daily reminder job
GET  /admin/stats           — system-wide stats snapshot
"""
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.user import User
from app.models.medication_log import MedicationLog
from app.models.reminder import ReminderSchedule
from app.models.schedule import MedicationSchedule
from app.services.sms import send_sms, reminder_message
from app.config import get_settings

EAT = ZoneInfo("Africa/Nairobi")  # UTC+3, no DST

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["Admin"], include_in_schema=False)

ADMIN_KEY = settings.SECRET_KEY  # reuse secret key for simplicity; use a separate key in prod


def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/run-reminders")
async def run_reminders(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    """
    Fire SMS reminders for:
      (1) legacy single-daily-time ReminderSchedule rows, and
      (2) interval-based MedicationSchedule rows created from the patient's
          "log a medication" form — this is the schedule type the frontend
          actually creates, so it MUST be checked here or reminders never fire.
    Runs hourly (see main.py's CronTrigger(minute=0)).
    """
    now_eat = datetime.now(EAT)
    today = now_eat.date()

    sent, skipped, failed = 0, 0, 0

    # ── (1) Legacy daily-time reminders ──────────────────────────────
    daily_schedules = (
        db.query(ReminderSchedule)
        .filter(ReminderSchedule.is_active.is_(True))
        .all()
    )
    for sched in daily_schedules:
        if sched.last_sent_at and sched.last_sent_at.astimezone(EAT).date() >= today:
            skipped += 1
            continue
        sched_hour = sched.reminder_time[:2]
        if now_eat.strftime("%H") != sched_hour:
            skipped += 1
            continue

        patient = db.query(User).filter(User.id == sched.patient_id).first()
        if not patient or not patient.phone:
            skipped += 1
            continue

        msg = reminder_message(patient.name)
        ok = await send_sms(patient.phone, msg)
        if ok:
            sched.last_sent_at = now_eat
            sent += 1
        else:
            failed += 1

    # ── (2) Interval-based medication schedules ──────────────────────
    interval_schedules = (
        db.query(MedicationSchedule)
        .filter(
            MedicationSchedule.active.is_(True),
            MedicationSchedule.start_date <= today,
            MedicationSchedule.end_date >= today,
        )
        .all()
    )
    for sched in interval_schedules:
        hh, mm = (int(p) for p in sched.first_dose_time.split(":"))
        start_dt = datetime(
            sched.start_date.year, sched.start_date.month, sched.start_date.day,
            hh, mm, tzinfo=EAT,
        )
        if now_eat < start_dt:
            skipped += 1
            continue

        elapsed_hours = (now_eat - start_dt).total_seconds() / 3600
        slot_index = int(elapsed_hours // sched.interval_hours)
        slot_time = start_dt + timedelta(hours=slot_index * sched.interval_hours)

        # Only send within the same hourly run window as the dose slot,
        # and only once per slot.
        if not (slot_time <= now_eat < slot_time + timedelta(hours=1)):
            skipped += 1
            continue
        if sched.last_reminder_sent_at and sched.last_reminder_sent_at >= slot_time:
            skipped += 1
            continue

        patient = db.query(User).filter(User.id == sched.patient_id).first()
        if not patient or not patient.phone:
            skipped += 1
            continue

        msg = reminder_message(patient.name, sched.medicine_name)
        ok = await send_sms(patient.phone, msg)
        if ok:
            sched.last_reminder_sent_at = now_eat
            sent += 1
        else:
            failed += 1

    db.commit()
    return {"sent": sent, "skipped": skipped, "failed": failed}


@router.get("/stats")
def system_stats(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    total_patients = db.query(User).filter(User.role == "patient").count()
    total_doctors = db.query(User).filter(User.role == "doctor").count()
    total_logs = db.query(MedicationLog).count()
    taken_logs = db.query(MedicationLog).filter(MedicationLog.taken.is_(True)).count()
    overall_rate = round(taken_logs / total_logs * 100) if total_logs else 0

    today = date.today()
    logs_today = db.query(MedicationLog).filter(MedicationLog.log_date == today).count()
    active_reminders = db.query(ReminderSchedule).filter(
        ReminderSchedule.is_active.is_(True)
    ).count()

    return {
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_logs": total_logs,
        "overall_adherence_rate": overall_rate,
        "logs_today": logs_today,
        "active_reminder_schedules": active_reminders,
    }