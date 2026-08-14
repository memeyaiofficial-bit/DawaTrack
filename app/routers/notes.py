"""

POST  /notes              — doctor sends a care note to a patient
GET   /notes/feed         — patient gets their own care feed (newest first)
PATCH /notes/{id}/read    — patient marks a note as read
GET   /notes/unread-count — patient gets unread count (for badge)
DELETE /notes/{id}        — doctor deletes their own note
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user, require_doctor, require_patient
from app.models.care_note import CareNote
from app.models.medication_log import MedicationLog
from app.models.user import User
from app.schemas.care_note import CareNoteCreate, CareNoteOut
from app.services.sms import send_sms, urgent_note_message
import asyncio

router = APIRouter(prefix="/notes", tags=["Care Notes"])


def _serialize_note(note: CareNote) -> CareNoteOut:
    doctor_name = note.doctor.name if note.doctor else None
    return CareNoteOut(
        id=note.id,
        doctor_id=note.doctor_id,
        doctor_name=doctor_name,
        patient_id=note.patient_id,
        log_id=note.log_id,
        message=note.message,
        note_type=note.note_type,
        is_read=note.is_read,
        created_at=note.created_at,
    )


@router.post("", response_model=CareNoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: CareNoteCreate,
    doctor: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    # Verify patient exists
    patient = db.query(User).filter(
        User.id == payload.patient_id, User.role == "patient"
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # If log_id is provided, verify it belongs to this patient
    if payload.log_id:
        log = db.query(MedicationLog).filter(
            MedicationLog.id == payload.log_id,
            MedicationLog.patient_id == payload.patient_id,
        ).first()
        if not log:
            raise HTTPException(
                status_code=404, detail="Medication log not found for this patient"
            )

    note = CareNote(
        doctor_id=doctor.id,
        patient_id=payload.patient_id,
        log_id=payload.log_id,
        message=payload.message,
        note_type=payload.note_type,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    # Fire-and-forget SMS for urgent notes if patient has a phone number
    if payload.note_type == "urgent" and patient.phone:
        async def _send():
            await send_sms(patient.phone, urgent_note_message(patient.name, doctor.name))
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_send())
        except RuntimeError:
            # If no running event loop (e.g. during tests), skip silently
            pass

    return _serialize_note(note)


@router.get("/feed", response_model=dict)
def get_care_feed(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """Patient's live care feed — newest first."""
    total = db.query(CareNote).filter(CareNote.patient_id == current_user.id).count()
    notes = (
        db.query(CareNote)
        .filter(CareNote.patient_id == current_user.id)
        .order_by(CareNote.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "notes": [_serialize_note(n) for n in notes],
    }


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    count = (
        db.query(CareNote)
        .filter(CareNote.patient_id == current_user.id, CareNote.is_read.is_(False))
        .count()
    )
    return {"unread": count}


@router.patch("/{note_id}/read", response_model=CareNoteOut)
def mark_read(
    note_id: int,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    note = db.query(CareNote).filter(
        CareNote.id == note_id, CareNote.patient_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.is_read = True
    db.commit()
    db.refresh(note)
    return _serialize_note(note)


@router.patch("/mark-all-read")
def mark_all_read(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    db.query(CareNote).filter(
        CareNote.patient_id == current_user.id, CareNote.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return {"detail": "All notes marked as read"}


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    doctor: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    note = db.query(CareNote).filter(
        CareNote.id == note_id, CareNote.doctor_id == doctor.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()

