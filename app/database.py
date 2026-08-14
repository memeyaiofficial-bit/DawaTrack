"""
SQLAlchemy engine, session factory, and Base for all models.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

# PostgreSQL — connection pool suited for web workloads
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # recycles stale connections
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass