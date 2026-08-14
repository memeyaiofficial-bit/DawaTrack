"""
Represents both patients and doctors — differentiated by `role`.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import ForeignKey
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum("patient", "doctor", "pharmacist", name="user_role"), nullable=False, default="patient"
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    doctor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    hospital: Mapped[str | None] = mapped_column(String(120), nullable=True, default="HAMAT Hospital")

    # Relationships
    medication_logs: Mapped[list["MedicationLog"]] = relationship(
        "MedicationLog", back_populates="patient", foreign_keys="MedicationLog.patient_id"
    )
    care_notes_sent: Mapped[list["CareNote"]] = relationship(
        "CareNote", back_populates="doctor", foreign_keys="CareNote.doctor_id"
    )
    care_notes_received: Mapped[list["CareNote"]] = relationship(
        "CareNote", back_populates="patient", foreign_keys="CareNote.patient_id"
    )
    reminder_schedule: Mapped["ReminderSchedule | None"] = relationship(
        "ReminderSchedule", back_populates="patient", uselist=False
    )

    # A doctor has many patients; each patient has one doctor (via doctor_id).
    # remote_side marks the "one" side of this self-referential relationship —
    # required here because both ends point at the same table (User).
    patients = relationship(
        "User",
        backref=backref("doctor", remote_side="User.id"),
        foreign_keys=[doctor_id],
    )