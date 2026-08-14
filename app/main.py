"""
app/main.py
FastAPI application factory.
Registers all routers, exception handlers, CORS, and the APScheduler
cron job that fires SMS reminders every hour.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx

from app.config import get_settings
from app.database import engine, Base
from app.routers import auth, logs, notes, patients, reminders, admin, caregivers, doctors, schedules, pharmacy
from app.utils.errors import (
    validation_exception_handler,
    integrity_error_handler,
    generic_exception_handler,
)

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── APScheduler ───────────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


async def hourly_reminder_job():
    """Calls the /admin/run-reminders endpoint internally once per hour."""
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            resp = await client.post(
                "/admin/run-reminders",
                headers={"x-admin-key": settings.SECRET_KEY},
                timeout=30,
            )
            data = resp.json()
            logger.info("Reminder job: %s", data)
    except Exception as exc:
        logger.error("Reminder job failed: %s", exc)


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (Alembic handles migrations in production, this is a safety net)
    Base.metadata.create_all(bind=engine)

    # Start scheduler — run at the top of every hour
    scheduler.add_job(
        hourly_reminder_job,
        CronTrigger(minute=0),   # fires at HH:00 every hour
        id="hourly_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started")

    yield

    scheduler.shutdown()
    logger.info("APScheduler stopped")


# ── App factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="DawaTrack API",
    description="Medication adherence platform for Kenyan hospitals",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:58003",
        "http://localhost:63342",

    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Routers
app.include_router(auth.router)
app.include_router(logs.router)
app.include_router(notes.router)
app.include_router(patients.router)
app.include_router(reminders.router)
app.include_router(admin.router)
app.include_router(caregivers.router)
app.include_router(doctors.router)
app.include_router(schedules.router)
app.include_router(pharmacy.router)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "app": "DawaTrack API", "version": "1.0.0"}