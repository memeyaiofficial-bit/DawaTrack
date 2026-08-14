"""
app/routers/logs.py

POST   /logs         — patient logs a dose
GET    /logs         — patient gets their own logs + stats
GET    /logs/{id}    — get single log
PATCH  /logs/{id}    — patient updates a log
DELETE /logs/{id}    — patient deletes a log
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from app.dependencies import get_db, get_current_user, require_patient
from app.models.medication_log import MedicationLog
from app.models.user import User
from app.schemas.medication_log import MedicationLogCreate, MedicationLogUpdate
from app.services.adherence import patient_stats

router = APIRouter(prefix="/logs", tags=["Medication Logs"])


def _get_log_or_404(log_id: int, patient_id: str, db: Session) -> MedicationLog:
    log = (
        db.query(MedicationLog)
        .options(selectinload(MedicationLog.care_notes))
        .filter(MedicationLog.id == log_id, MedicationLog.patient_id == patient_id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


def _serialize_log(log: MedicationLog, db: Session) -> dict:
    """Serialize a log resolving doctor_name on each care note."""
    care_notes = []
    for note in (log.care_notes or []):
        doctor_name = None
        if note.doctor_id:
            doc = db.query(User).filter(User.id == note.doctor_id).first()
            doctor_name = doc.name if doc else None
        care_notes.append({
            "id": note.id,
            "doctor_id": note.doctor_id,
            "doctor_name": doctor_name,
            "message": note.message,
            "note_type": note.note_type,
            "is_read": note.is_read,
            "created_at": note.created_at,
        })
    return {
        "id": log.id,
        "patient_id": log.patient_id,
        "medicine_name": log.medicine_name,
        "log_date": log.log_date,
        "taken": log.taken,
        "time_taken": log.time_taken,
        "notes": log.notes,
        "logged_at": log.logged_at,
        "care_notes": care_notes,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_log(
    payload: MedicationLogCreate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    log = MedicationLog(
        patient_id=current_user.id,
        medicine_name=payload.medicine_name,
        log_date=payload.log_date,
        taken=payload.taken,
        time_taken=payload.time_taken,
        notes=payload.notes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    log = _get_log_or_404(log.id, current_user.id, db)
    return _serialize_log(log, db)


@router.get("")
def list_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Use /patients/{id}/logs as a doctor")

    total = (
        db.query(MedicationLog)
        .filter(MedicationLog.patient_id == current_user.id)
        .count()
    )
    logs = (
        db.query(MedicationLog)
        .options(selectinload(MedicationLog.care_notes))
        .filter(MedicationLog.patient_id == current_user.id)
        .order_by(MedicationLog.log_date.desc(), MedicationLog.logged_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    stats = patient_stats(current_user.id, db)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "stats": stats,
        "logs": [_serialize_log(l, db) for l in logs],
    }


@router.get("/{log_id}")
def get_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "patient":
        log = _get_log_or_404(log_id, current_user.id, db)
    else:
        log = (
            db.query(MedicationLog)
            .options(selectinload(MedicationLog.care_notes))
            .filter(MedicationLog.id == log_id)
            .first()
        )
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
    return _serialize_log(log, db)


@router.patch("/{log_id}")
def update_log(
    log_id: int,
    payload: MedicationLogUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    log = _get_log_or_404(log_id, current_user.id, db)
    if payload.taken is not None:
        log.taken = payload.taken
    if payload.notes is not None:
        log.notes = payload.notes
    if payload.time_taken is not None:
        log.time_taken = payload.time_taken
    db.commit()
    log = _get_log_or_404(log_id, current_user.id, db)
    return _serialize_log(log, db)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(
    log_id: int,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    log = _get_log_or_404(log_id, current_user.id, db)
    db.delete(log)
    db.commit()