"""
Per-patient SMS reminder schedule.
APScheduler uses these rows to send daily reminders via Africa's Talking.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ReminderSchedule(Base):
    __tablename__ = "reminder_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # Time in HH:MM format (EAT, Africa/Nairobi)
    reminder_time: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Track last SMS to avoid duplicate sends
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Streak tracking: consecutive days with at least one dose logged
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    patient: Mapped["User"] = relationship("User", back_populates="reminder_schedule")