"""
app/schemas/pharmacy.py
"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


# ── Medicine requests (patient → pharmacy) ──────────────────────────
class MedicineRequestCreate(BaseModel):
    medicine_name: str
    dosage: str | None = None
    message: str | None = None


class MedicineRequestReply(BaseModel):
    pharmacy_reply: str
    status: Literal["replied", "fulfilled", "unavailable"] = "replied"


class MedicineRequestOut(BaseModel):
    id: int
    patient_id: str
    patient_name: str | None = None
    medicine_name: str
    dosage: str | None = None
    message: str | None = None
    status: str
    pharmacy_reply: str | None = None
    pharmacist_name: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_orm = True


# ── Dispense records (pharmacy → patient) ───────────────────────────
class DispenseCreate(BaseModel):
    patient_id: str | None = None
    patient_name: str
    medicine_name: str
    dosage: str | None = None
    quantity: int = 1
    status: Literal["dispensed", "pending", "unavailable"] = "dispensed"
    smart_card: str = "none"
    notes: str | None = None


class DispenseOut(BaseModel):
    id: int
    patient_id: str | None = None
    patient_name: str
    pharmacist_name: str | None = None
    medicine_name: str
    dosage: str | None = None
    quantity: int
    status: str
    smart_card: str
    discount_pct: int
    notes: str | None = None
    created_at: datetime

    class Config:
        from_orm = True
