"""
app/models/pharmacy.py
Backend-persisted replacement for the old localStorage-only pharmacy
bridge (dt_med_requests / dt_disp_log). These are the tables the
pharmacy dashboard, patient dashboard, and doctor dashboard now all
read/write through the real API instead of the browser's local storage.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MedicineRequest(Base):
    """A patient's 'I'm out of medicine / need a refill' request."""
    __tablename__ = "medicine_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "replied", "fulfilled", "unavailable", name="request_status"),
        nullable=False, default="pending",
    )
    pharmacy_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    pharmacist_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id])
    pharmacist: Mapped["User | None"] = relationship("User", foreign_keys=[pharmacist_id])


class DispenseRecord(Base):
    """A record of medicine actually handed to a patient at the pharmacy counter."""
    __tablename__ = "dispense_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Free-text fallback for a walk-in who isn't a registered DawaTrack patient
    patient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    pharmacist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    medicine_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("dispensed", "pending", "unavailable", name="dispense_status"),
        nullable=False, default="dispensed",
    )
    smart_card: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    discount_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    patient: Mapped["User | None"] = relationship("User", foreign_keys=[patient_id])
    pharmacist: Mapped["User | None"] = relationship("User", foreign_keys=[pharmacist_id])
