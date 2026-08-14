"""
reminder schema
"""
from datetime import datetime
from pydantic import BaseModel, field_validator
import re


class ReminderScheduleCreate(BaseModel):
    reminder_time: str = "08:00"   # HH:MM

    @field_validator("reminder_time")
    @classmethod
    def valid_time(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("reminder_time must be HH:MM format")
        h, m = map(int, v.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError("Invalid time value")
        return v


class ReminderScheduleUpdate(BaseModel):
    reminder_time: str | None = None
    is_active: bool | None = None

    @field_validator("reminder_time")
    @classmethod
    def valid_time(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("reminder_time must be HH:MM format")
        return v


class ReminderScheduleOut(BaseModel):
    id: int
    patient_id: str
    reminder_time: str
    is_active: bool
    last_sent_at: datetime | None
    streak_days: int
    created_at: datetime

    model_config = {"from_attributes": True}