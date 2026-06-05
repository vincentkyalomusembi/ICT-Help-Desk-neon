from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    SESSION_EXPIRE_MINUTES: int
    LOCKOUT_DURATION_MINUTES: int

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        case_sensitive=True,
    )


settings = Settings()