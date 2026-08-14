"""
All environment configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Doctor registration gate
    DOCTOR_ACCESS_CODE: str = "DOC2026"
    PHARMACY_ACCESS_CODE: str = "PH2026"

    # TalkSasa SMS
    TALKSASA_API_KEY: str = ""
    TALKSASA_SENDER_ID: str = "DawaTrack"


    # App
    APP_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:5500"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()