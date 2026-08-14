"""
app/schemas/medication_log.py
"""
from datetime import datetime, date
from pydantic import BaseModel, validator


class MedicationLogCreate(BaseModel):
    medicine_name: str
    log_date: date
    taken: bool
    time_taken: str | None = None
    notes: str | None = None

    @validator("medicine_name")
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Medicine name cannot be empty")
        return v.strip()


class MedicationLogUpdate(BaseModel):
    taken: bool | None = None
    notes: str | None = None
    time_taken: str | None = None


class CareNoteInLog(BaseModel):
    id: int
    doctor_id: str | None = None
    doctor_name: str | None = None      # ← optional — resolved manually
    message: str
    note_type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_orm = True


class MedicationLogOut(BaseModel):
    id: int
    patient_id: str
    medicine_name: str
    log_date: date
    taken: bool
    time_taken: str | None = None
    notes: str | None = None
    logged_at: datetime
    care_notes: list[CareNoteInLog] = []

    class Config:
        from_orm = True