"""
One row per medication dose event logged by a patient.
"""
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MedicationLog(Base):
    __tablename__ = "medication_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(200), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    taken: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_taken: Mapped[str | None] = mapped_column(String(10), nullable=True)   # "08:30"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    patient: Mapped["User"] = relationship(
        "User", back_populates="medication_logs", foreign_keys=[patient_id]
    )
    care_notes: Mapped[list["CareNote"]] = relationship(
        "CareNote", back_populates="log", cascade="all, delete-orphan"
    )