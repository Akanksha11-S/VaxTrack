"""Application settings, read once from environment variables (and an optional .env file)."""
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

log = logging.getLogger("vaxtrack")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL") or f"sqlite:///{(BASE_DIR / 'vaxtrack.db').as_posix()}"
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR") or BASE_DIR / "storage" / "uploads")
    MAX_UPLOAD_MB: int = _int("MAX_UPLOAD_MB", 10)
    MAX_PDF_PAGES: int = _int("MAX_PDF_PAGES", 6)
    DOCUMENT_RETENTION_DAYS: int = _int("DOCUMENT_RETENTION_DAYS", 30)
    TOKEN_EXPIRE_MINUTES: int = _int("TOKEN_EXPIRE_MINUTES", 720)
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in (os.getenv("CORS_ORIGINS") or "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if o.strip()
    ]
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "").strip()

    # Optional SMTP settings for scheduled reminder emails.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = _int("SMTP_PORT", 587)
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_FROM: str = os.getenv("SMTP_FROM", "").strip()
    REMINDER_CHECK_INTERVAL_SECONDS: int = _int("REMINDER_CHECK_INTERVAL_SECONDS", 21600)

    # Optional LLM used only to simplify text typed on the Vaccine information page.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none").strip().lower()  # none | anthropic | openai
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "").strip()
    LLM_MODEL: str = os.getenv("LLM_MODEL", "").strip()
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "").strip()

    DEFAULT_SCHEDULE_KEY: str = os.getenv("DEFAULT_SCHEDULE_KEY", "in-uip")

    _secret = os.getenv("SECRET_KEY", "").strip()
    if not _secret or _secret.startswith("change-me"):
        _secret = secrets.token_urlsafe(48)
        log.warning("SECRET_KEY is not set - using a temporary key. Sessions end when the server restarts.")
    SECRET_KEY: str = _secret

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        return self.LLM_PROVIDER in {"anthropic", "openai"} and bool(self.LLM_API_KEY)


settings = Settings()
