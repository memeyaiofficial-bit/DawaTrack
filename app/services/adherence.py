"""
Pure functions for calculating adherence statistics.
Used by both the patient and doctor routers.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.medication_log import MedicationLog
from app.models.user import User


def adherence_rate(logs: list[MedicationLog]) -> int:
    """Return adherence percentage (0-100) for a list of logs."""
    if not logs:
        return 0
    taken = sum(1 for l in logs if l.taken)
    return round(taken / len(logs) * 100)


def patient_stats(patient_id: str, db: Session) -> dict:
    """Full stats for one patient."""
    logs = (
        db.query(MedicationLog)
        .filter(MedicationLog.patient_id == patient_id)
        .order_by(MedicationLog.log_date.desc())
        .all()
    )
    total = len(logs)
    taken = sum(1 for l in logs if l.taken)
    missed = total - taken
    rate = adherence_rate(logs)

    # Last 7 days trend
    today = date.today()
    trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_logs = [l for l in logs if l.log_date == d]
        trend.append(
            {
                "date": d.isoformat(),
                "rate": adherence_rate(day_logs) if day_logs else None,
                "taken": sum(1 for l in day_logs if l.taken),
                "missed": sum(1 for l in day_logs if not l.taken),
            }
        )

    return {
        "total": total,
        "taken": taken,
        "missed": missed,
        "rate": rate,
        "trend_7d": trend,
    }


def doctor_overview(doctor_patients: list[User], db: Session) -> dict:
    """Aggregate stats across all patients for a doctor's KPI tiles."""
    rates = []
    at_risk_count = 0
    total_logs = 0

    for patient in doctor_patients:
        logs = db.query(MedicationLog).filter(
            MedicationLog.patient_id == patient.id
        ).all()
        total_logs += len(logs)
        r = adherence_rate(logs)
        rates.append(r)
        if r < 60:
            at_risk_count += 1

    avg_rate = round(sum(rates) / len(rates)) if rates else 0

    return {
        "total_patients": len(doctor_patients),
        "avg_adherence": avg_rate,
        "at_risk_count": at_risk_count,
        "total_logs": total_logs,
    }