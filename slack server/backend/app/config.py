import os
import logging
from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production-use-strong-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ── Slack ──────────────────────────────────────────────────────
    SLACK_BOT_TOKEN: str = ""
    SLACK_APP_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_CLIENT_ID: str = ""
    SLACK_CLIENT_SECRET: str = ""
    SLACK_REDIRECT_URI: str = "http://localhost:8000/auth/slack/callback"

    # ── Supabase ───────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""   # service_role key — never expose to frontend
    SUPABASE_ANON_KEY: str = ""      # anon/public key  — safe for frontend

    # ── Groq LLM ──────────────────────────────────────────────────
    GROQ_API_KEY: str = ""

    # ── Email (optional) ──────────────────────────────────────────
    EMAIL_ENABLED: bool = False
    EMAIL_SENDER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_RECIPIENT: str = ""
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    # ── Monitor ───────────────────────────────────────────────────
    MONITOR_CHANNELS: str = ""
    CHECK_INTERVAL_MINUTES: int = 15
    DATA_DIR: str = "monitor_data"
    NOTIFICATION_USER_ID: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
