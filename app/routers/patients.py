"""
app/routers/patients.py
Doctor-only endpoints for viewing and managing their patient panel.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from app.dependencies import get_db, require_doctor, require_pharmacist
from app.models.user import User
from app.models.medication_log import MedicationLog
from app.models.care_note import CareNote
from app.schemas.user import UserOut
from app.services.adherence import patient_stats, doctor_overview

router = APIRouter(prefix="/patients", tags=["Patients (Doctor)"])


def _get_own_patient(patient_id: str, doctor: User, db: Session) -> User:
    """Fetch a patient, 404ing if they don't exist OR aren't this doctor's patient.
    (404, not 403 — so an unassigned/other-doctor's patient ID doesn't leak
    the fact that it belongs to someone.)"""
    patient = db.query(User).filter(
        User.id == patient_id, User.role == "patient", User.doctor_id == doctor.id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _patient_summary(patient: User, db: Session) -> dict:
    stats = patient_stats(patient.id, db)
    return {
        "id": patient.id,
        "name": patient.name,
        "email": patient.email,
        "phone": patient.phone,
        "created_at": patient.created_at,
        **stats,
    }


def _serialize_log(log: MedicationLog, db: Session) -> dict:
    """Manually serialize a log with doctor_name resolved on care notes."""
    care_notes = []
    for note in (log.care_notes or []):
        # Resolve doctor name
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


@router.get("", response_model=dict)
def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    filter: str = Query("all", pattern="^(all|atrisk|good|fair)$"),
    doctor: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    patients = (
        db.query(User)
        .filter(
            User.role == "patient",
            User.is_active.is_(True),
            User.doctor_id == doctor.id,
        )
        .order_by(User.name)
        .all()
    )
    summaries = [_patient_summary(p, db) for p in patients]

    if filter == "atrisk":
        summaries = [p for p in summaries if p["rate"] < 60]
    elif filter == "fair":
        summaries = [p for p in summaries if 60 <= p["rate"] < 80]
    elif filter == "good":
        summaries = [p for p in summaries if p["rate"] >= 80]

    total = len(summaries)
    page  = summaries[skip: skip + limit]
    return {"total": total, "skip": skip, "limit": limit, "patients": page}


@router.get("/overview")
def doctor_dashboard_overview(
    doctor: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    patients = (
        db.query(User)
        .filter(
            User.role == "patient",
            User.is_active.is_(True),
            User.doctor_id == doctor.id,
        )
        .all()
    )
    unassigned_count = (
        db.query(User)
        .filter(User.role == "patient", User.is_active.is_(True), User.doctor_id.is_(None))
        .count()
    )
    overview = doctor_overview(patients, db)
    overview["unassigned_count"] = unassigned_count
    return overview


@router.get("/{patient_id}", response_model=dict)
def get_patient(
    patient_id: str,
    doctor: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    patient = _get_own_patient(patient_id, doctor, db)
    return _patient_summary(patient, db)


@router.get("/{patient_id}/logs", response_model=dict)
def get_patient_logs(
    patient_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    doctor: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    patient = _get_own_patient(patient_id, doctor, db)

    total = db.query(MedicationLog).filter(
        MedicationLog.patient_id == patient_id
    ).count()

    logs = (
        db.query(MedicationLog)
        .options(selectinload(MedicationLog.care_notes))
        .filter(MedicationLog.patient_id == patient_id)
        .order_by(MedicationLog.log_date.desc(), MedicationLog.logged_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "patient": UserOut.model_validate(patient),
        "logs": [_serialize_log(l, db) for l in logs],  # ← uses manual serializer
    }


@router.get("/{patient_id}/trend")
def get_patient_trend(
    patient_id: str,
    doctor: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    patient = _get_own_patient(patient_id, doctor, db)

    stats = patient_stats(patient_id, db)
    return {
        "patient_id": patient_id,
        "patient_name": patient.name,
        "trend_7d": stats["trend_7d"],
        "rate": stats["rate"],
    }



@router.get("/search")
def search_patients(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    # Pharmacists need to look up any registered patient at the counter.
    # Doctors already get a scoped, filterable panel via GET /patients —
    # they don't need (and shouldn't have) unrestricted cross-patient search.
    current_user: User = Depends(require_pharmacist),
    db: Session = Depends(get_db),
):
    like = f"%{q}%"
    patients = (
        db.query(User)
        .filter(User.role == "patient")
        .filter((User.name.ilike(like)) | (User.email.ilike(like)) | (User.id.ilike(like)))
        .limit(limit)
        .all()
    )
    result = []
    for p in patients:
        logs = db.query(MedicationLog).filter(MedicationLog.patient_id == p.id).all()
        rate = round(sum(1 for l in logs if l.taken) / len(logs) * 100) if logs else 0
        result.append({
            "id": p.id, "name": p.name, "email": p.email, "phone": p.phone,
            "total_logs": len(logs), "adherence_rate": rate,
        })
    return result