"""
app/models/schedule.py
"""
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, Date, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(150), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    interval_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    first_dose_time: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00")  # "HH:MM"
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Tracks the last dose-slot an SMS reminder was sent for, so the hourly
    # job doesn't double-send within the same interval window.
    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )