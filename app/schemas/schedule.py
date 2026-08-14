"""
app/schemas/schedule.py
"""
from datetime import date, datetime
from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    medicine_name: str
    dosage: str | None = None
    start_date: date
    end_date: date
    interval_hours: int
    first_dose_time: str = "08:00"
    notes: str | None = None


class ScheduleUpdate(BaseModel):
    active: bool | None = None


class ScheduleOut(BaseModel):
    id: int
    patient_id: str
    medicine_name: str
    dosage: str | None = None
    start_date: date
    end_date: date
    interval_hours: int
    first_dose_time: str
    notes: str | None = None
    active: bool
    created_at: datetime

    class Config:
        from_orm = True