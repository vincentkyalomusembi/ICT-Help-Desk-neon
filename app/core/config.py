import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env", override=True)


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    SESSION_EXPIRE_MINUTES: int
    LOCKOUT_DURATION_MINUTES: int
    MAGIC_LINK_EXPIRE_MINUTES: int
    BREVO_API_KEY: str
    BREVO_SENDER_EMAIL: str
    BREVO_SENDER_NAME: str
    FRONTEND_BASE_URL: str

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()

if not settings.BREVO_API_KEY.startswith("xkeysib-"):
    raise RuntimeError(
        f"Invalid BREVO_API_KEY — expected xkeysib- prefix, got: {settings.BREVO_API_KEY[:12]}..."
    )