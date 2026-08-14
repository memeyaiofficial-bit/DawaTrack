"""
care_note schema
"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class CareNoteCreate(BaseModel):
    patient_id: str
    log_id: int | None = None
    message: str
    note_type: Literal["advice", "reminder", "praise", "urgent"] = "advice"


class CareNoteOut(BaseModel):
    id: int
    doctor_id: str | None
    doctor_name: str | None       # resolved from doctor relationship
    patient_id: str
    log_id: int | None
    message: str
    note_type: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}