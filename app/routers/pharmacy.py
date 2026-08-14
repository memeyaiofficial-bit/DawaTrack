"""
app/routers/pharmacy.py

Real backend for the pharmacy dashboard. This replaces the old
localStorage-only bridge (dt_med_requests / dt_disp_log / dt_ph_notes)
that never actually reached the database — meaning the pharmacy
dashboard could never see real, registered patients.

  Patient-facing:
    POST /requests            — flag "I'm out of medicine"
    GET  /requests/mine        — my own requests + pharmacy replies
    GET  /dispense/mine        — my own dispensing history

  Pharmacist-facing (require_pharmacist):
    GET   /requests             — all requests (optional ?status=pending)
    PATCH /requests/{id}        — reply + update status
    POST  /dispense              — record a dispensed medicine
    GET   /dispense              — dispensing log (optional ?q= search)
    GET   /patients/{id}/profile — patient summary + logs + dispense history
    PATCH /patients/{id}/logs/{log_id} — update a dose's taken/missed/dispensed status
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_patient, require_pharmacist, require_staff
from app.models.user import User
from app.models.medication_log import MedicationLog
from app.models.pharmacy import MedicineRequest, DispenseRecord
from app.schemas.pharmacy import (
    MedicineRequestCreate, MedicineRequestReply, MedicineRequestOut,
    DispenseCreate, DispenseOut,
)
from app.routers.patients import _patient_summary, _serialize_log

router = APIRouter(tags=["Pharmacy"])

CARD_DISCOUNTS = {"HMT-BAS": 10, "HMT-PLU": 20, "HMT-FAM": 30}


def _request_out(r: MedicineRequest) -> dict:
    return {
        "id": r.id,
        "patient_id": r.patient_id,
        "patient_name": r.patient.name if r.patient else None,
        "medicine_name": r.medicine_name,
        "dosage": r.dosage,
        "message": r.message,
        "status": r.status,
        "pharmacy_reply": r.pharmacy_reply,
        "pharmacist_name": r.pharmacist.name if r.pharmacist else None,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _dispense_out(d: DispenseRecord) -> dict:
    return {
        "id": d.id,
        "patient_id": d.patient_id,
        "patient_name": d.patient_name,
        "pharmacist_name": d.pharmacist.name if d.pharmacist else None,
        "medicine_name": d.medicine_name,
        "dosage": d.dosage,
        "quantity": d.quantity,
        "status": d.status,
        "smart_card": d.smart_card,
        "discount_pct": d.discount_pct,
        "notes": d.notes,
        "created_at": d.created_at,
    }


# ══════════════════ PATIENT-FACING ══════════════════════════════════

@router.post("/requests", response_model=MedicineRequestOut, status_code=201)
def create_request(
    payload: MedicineRequestCreate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    req = MedicineRequest(
        patient_id=current_user.id,
        medicine_name=payload.medicine_name,
        dosage=payload.dosage,
        message=payload.message or "Medicine out — requesting refill.",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _request_out(req)


@router.get("/requests/mine", response_model=list[MedicineRequestOut])
def my_requests(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    reqs = (
        db.query(MedicineRequest)
        .filter(MedicineRequest.patient_id == current_user.id)
        .order_by(MedicineRequest.created_at.desc())
        .all()
    )
    return [_request_out(r) for r in reqs]


@router.get("/dispense/mine", response_model=list[DispenseOut])
def my_dispense_history(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    recs = (
        db.query(DispenseRecord)
        .filter(DispenseRecord.patient_id == current_user.id)
        .order_by(DispenseRecord.created_at.desc())
        .all()
    )
    return [_dispense_out(r) for r in recs]


# ══════════════════ PHARMACIST-FACING ═══════════════════════════════

@router.get("/requests", response_model=list[MedicineRequestOut])
def list_requests(
    status: str | None = Query(None, pattern="^(pending|replied|fulfilled|unavailable)$"),
    # Doctors get read-only visibility (matches the doctor dashboard's
    # requests preview panel); only pharmacists can reply/fulfill.
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    q = db.query(MedicineRequest)
    if status:
        q = q.filter(MedicineRequest.status == status)
    reqs = q.order_by(MedicineRequest.created_at.desc()).all()
    return [_request_out(r) for r in reqs]


@router.patch("/requests/{request_id}", response_model=MedicineRequestOut)
def reply_to_request(
    request_id: int,
    payload: MedicineRequestReply,
    current_user: User = Depends(require_pharmacist),
    db: Session = Depends(get_db),
):
    req = db.query(MedicineRequest).filter(MedicineRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.pharmacy_reply = payload.pharmacy_reply
    req.status = payload.status
    req.pharmacist_id = current_user.id
    db.commit()
    db.refresh(req)
    return _request_out(req)


@router.post("/dispense", response_model=DispenseOut, status_code=201)
def create_dispense(
    payload: DispenseCreate,
    current_user: User = Depends(require_pharmacist),
    db: Session = Depends(get_db),
):
    if payload.patient_id:
        patient = db.query(User).filter(
            User.id == payload.patient_id, User.role == "patient"
        ).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

    pct = CARD_DISCOUNTS.get(payload.smart_card, 0)
    rec = DispenseRecord(
        patient_id=payload.patient_id,
        patient_name=payload.patient_name,
        pharmacist_id=current_user.id,
        medicine_name=payload.medicine_name,
        dosage=payload.dosage,
        quantity=payload.quantity,
        status=payload.status,
        smart_card=payload.smart_card,
        discount_pct=pct,
        notes=payload.notes,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _dispense_out(rec)


@router.get("/dispense", response_model=list[DispenseOut])
def list_dispense(
    q: str | None = Query(None, min_length=1),
    current_user: User = Depends(require_pharmacist),
    db: Session = Depends(get_db),
):
    query = db.query(DispenseRecord)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (DispenseRecord.patient_name.ilike(like)) | (DispenseRecord.medicine_name.ilike(like))
        )
    recs = query.order_by(DispenseRecord.created_at.desc()).all()
    return [_dispense_out(r) for r in recs]


@router.get("/patients/{patient_id}/profile", response_model=dict)
def pharmacist_patient_profile(
    patient_id: str,
    current_user: User = Depends(require_pharmacist),
    db: Session = Depends(get_db),
):
    """Unlike the doctor's /patients/{id} endpoint, a pharmacist can look up
    ANY registered patient (not just ones assigned to a particular doctor) —
    that's a normal pharmacy-counter workflow, not a privacy leak, since
    pharmacists legitimately need to serve any patient who walks in."""
    patient = db.query(User).filter(
        User.id == patient_id, User.role == "patient"
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    logs = (
        db.query(MedicationLog)
        .filter(MedicationLog.patient_id == patient_id)
        .order_by(MedicationLog.log_date.desc(), MedicationLog.logged_at.desc())
        .all()
    )
    dispense_history = (
        db.query(DispenseRecord)
        .filter(DispenseRecord.patient_id == patient_id)
        .order_by(DispenseRecord.created_at.desc())
        .all()
    )

    return {
        "patient": _patient_summary(patient, db),
        "logs": [_serialize_log(l, db) for l in logs],
        "dispense_history": [_dispense_out(r) for r in dispense_history],
    }


@router.patch("/patients/{patient_id}/logs/{log_id}", response_model=dict)
def pharmacist_update_dose_status(
    patient_id: str,
    log_id: int,
    status: str = Query(..., pattern="^(taken|missed|dispensed)$"),
    current_user: User = Depends(require_pharmacist),
    db: Session = Depends(get_db),
):
    log = db.query(MedicationLog).filter(
        MedicationLog.id == log_id, MedicationLog.patient_id == patient_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    log.taken = status in ("taken", "dispensed")

    if status == "dispensed":
        patient = db.query(User).filter(User.id == patient_id).first()
        db.add(DispenseRecord(
            patient_id=patient_id,
            patient_name=patient.name if patient else patient_id,
            pharmacist_id=current_user.id,
            medicine_name=log.medicine_name,
            quantity=1,
            status="dispensed",
            notes="Status updated from patient profile",
        ))

    db.commit()
    return {"ok": True, "log_id": log_id, "status": status}
