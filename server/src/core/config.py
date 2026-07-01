"""Typed application settings (NUMA-102).

Single source of environment configuration via pydantic-settings. Additive: not
yet wired into call sites. Scattered os.getenv usage is migrated here
incrementally (PLAN 5.1, 22.1).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    jwt_secret: str = ""

    frontend_url: str = ""
    backend_url: str = ""

    numa_encryption_key: str = ""

    timezone: str = "Asia/Kolkata"
    sync_scheduler_interval_minutes: int = 30
    leetcode_username: str = ""

    @property
    def is_dev(self) -> bool:
        return not self.frontend_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
