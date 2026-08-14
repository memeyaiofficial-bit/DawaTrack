"""
All environment configuration
"""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Prefer Render environment variables in production; keep local .env support for development.
        app_env = os.getenv("APP_ENV", "development").lower()
        if app_env == "production":
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()