"""Typed application settings (NUMA-102).

Single source of environment configuration via pydantic-settings. Additive: not
yet wired into call sites. Scattered os.getenv usage is migrated here
incrementally (PLAN 5.1, 22.1).
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, like every other loader in the tree (core/db.py, auth/service.py,
# main.py all resolve from __file__). pydantic-settings resolves a relative
# env_file against the working directory, so starting from the repo root or a
# systemd unit above server/ found no file at all - and since every field has a
# "" default, that surfaced as empty credentials rather than a boot failure.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore", case_sensitive=False)

    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    jwt_secret: str = ""

    frontend_url: str = ""
    backend_url: str = ""

    numa_encryption_key: str = ""

    # Declared, never inferred. Defaulting to production means a deploy that
    # forgets to set it fails closed.
    numa_env: str = "production"

    timezone: str = "Asia/Kolkata"
    sync_scheduler_interval_minutes: int = 30
    leetcode_username: str = ""

    @property
    def is_dev(self) -> bool:
        """True only when the environment says so.

        This returned `not self.frontend_url`, the exact inference NUMA-127
        deleted from `main.py` because a deploy that forgot FRONTEND_URL
        silently opened CORS to every origin. Leaving it here meant the first
        caller to follow this module's docstring would reintroduce the
        vulnerability (NUMA-142 P6, PLAN 8).
        """
        return self.numa_env.strip().lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
