"""
Doctor-authored notes attached to a specific medication log entry.
Patients read these live via the Care Feed.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CareNote(Base):
    __tablename__ = "care_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_id: Mapped[int | None] = mapped_column(
        ForeignKey("medication_logs.id", ondelete="SET NULL"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[str] = mapped_column(
        SAEnum("advice", "reminder", "praise", "urgent", name="note_type"),
        nullable=False,
        default="advice",
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    doctor: Mapped["User"] = relationship(
        "User", back_populates="care_notes_sent", foreign_keys=[doctor_id]
    )
    patient: Mapped["User"] = relationship(
        "User", back_populates="care_notes_received", foreign_keys=[patient_id]
    )
    log: Mapped["MedicationLog | None"] = relationship(
        "MedicationLog", back_populates="care_notes"
    )