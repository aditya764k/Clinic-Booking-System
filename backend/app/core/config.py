"""
Application configuration via pydantic-settings.

All secrets are read from environment variables / .env file.
Never hardcode secrets here — this module only declares the schema.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # ── Google OAuth ─────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # ── Cookie / CORS ─────────────────────────────────────────────────────────
    # Set COOKIE_SECURE=false for local http dev; True in production (https only)
    COOKIE_SECURE: bool = True
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # ── Legacy / other services ───────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 12

    model_config = SettingsConfigDict(
        # Try to load from clinic-app/.env relative to this file's location
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        env_file_encoding="utf-8",
        # Also accept already-set env vars (Docker injects them)
        extra="ignore",
    )


# Module-level singleton — import this everywhere
settings = Settings()
