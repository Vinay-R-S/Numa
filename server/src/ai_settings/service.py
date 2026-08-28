"""AI settings business logic (NUMA-119 P5, PLAN 2.1 / 5.2 / 21.1).

Provider/model validation, API-key encryption, the response mapping and the
integration-key env-file handling were extracted verbatim from `router.py`,
which is now HTTP-only. Behavior is unchanged: the same messages, the same
`.env` rewrite rules and the same response shapes.
"""
from __future__ import annotations

import os

from ..core.base import BaseService
from ..core.llm_factory import (
    PROVIDER_MODELS,
    encrypt_api_key,
    get_available_providers,
)
from .constants import ENV_FILE_PATH, INTEGRATION_KEYS, NON_SECRET_KEYS
from .repository import AISettingsRepository, ai_settings_repository
from .schemas import (
    AISettingsResponse,
    AISettingsUpdate,
    ProviderInfo,
    ProvidersListResponse,
)


class AISettingsError(Exception):
    """Invalid request the caller can fix. Mapped to 400."""


class AISettingsSaveError(Exception):
    """Persistence failure. Mapped to 500."""


def _row_to_response(row: dict) -> AISettingsResponse:
    return AISettingsResponse(
        provider=row["provider"],
        model_id=row["model_id"],
        has_api_key=bool(row.get("encrypted_api_key")),
        ollama_base_url=row.get("ollama_base_url"),
        temperature=row.get("temperature", 0.1),
    )


class AISettingsService(BaseService):
    """Per-user LLM provider/model config plus server-wide integration keys."""

    def __init__(self, repository: AISettingsRepository | None = None) -> None:
        super().__init__()
        self.repository = repository or ai_settings_repository

    def get_settings(self, user_id: str) -> ProvidersListResponse:
        providers = [ProviderInfo(**p) for p in get_available_providers()]
        row = self.repository.get(user_id)
        current = _row_to_response(row) if row else None
        return ProvidersListResponse(providers=providers, current=current)

    def update_settings(self, user_id: str, body: AISettingsUpdate) -> AISettingsResponse:
        if body.provider not in PROVIDER_MODELS:
            raise AISettingsError(f"Unsupported provider: {body.provider}")

        if body.model_id not in PROVIDER_MODELS[body.provider]:
            raise AISettingsError(
                f"Model '{body.model_id}' not available for {body.provider}. "
                f"Choose from: {PROVIDER_MODELS[body.provider]}"
            )

        encrypted = None
        if body.api_key and body.api_key.strip():
            encrypted = encrypt_api_key(body.api_key.strip())

        try:
            result = self.repository.upsert(
                user_id=user_id,
                provider=body.provider,
                model_id=body.model_id,
                encrypted=encrypted,
                ollama_base_url=body.ollama_base_url,
                temperature=body.temperature,
                include_key=bool(encrypted),
            )
        except Exception as exc:
            raise AISettingsSaveError(f"Failed to save AI settings: {exc}") from exc

        return _row_to_response(result)

    def reset_settings(self, user_id: str) -> None:
        """Drop the user's row so the env-var defaults apply again."""
        self.repository.delete(user_id)

    def read_integration_keys(self) -> dict:
        """One boolean per known key, plus `<key>_value` for the non-secret ones."""
        keys_status: dict = {
            api_key: bool(os.getenv(env_key, "").strip())
            for api_key, env_key in INTEGRATION_KEYS.items()
        }

        for api_key in NON_SECRET_KEYS:
            value = os.getenv(INTEGRATION_KEYS[api_key], "").strip()
            if value:
                keys_status[f"{api_key}_value"] = value

        return keys_status

    def update_integration_keys(self, body: dict) -> dict:
        """Write the known keys into the server `.env` and the live environment."""
        lines: list[str] = []
        if ENV_FILE_PATH.exists():
            lines = ENV_FILE_PATH.read_text().splitlines()

        updated_keys: list[str] = []
        for api_key, value in body.items():
            env_key = INTEGRATION_KEYS.get(api_key)
            if not env_key or not isinstance(value, str):
                continue

            _upsert_env_line(lines, env_key, value)
            os.environ[env_key] = value
            updated_keys.append(api_key)

        # Nothing recognized in the body: leave the file alone instead of
        # rewriting it, which would normalize its line endings for no reason.
        if not updated_keys:
            return {"ok": True, "updated": updated_keys}

        ENV_FILE_PATH.write_text("\n".join(lines) + "\n")

        return {"ok": True, "updated": updated_keys}


def _upsert_env_line(lines: list[str], env_key: str, value: str) -> None:
    """Replace the first `KEY=`/`KEY =` line in place, else append a new one."""
    for i, line in enumerate(lines):
        if line.startswith(f"{env_key}=") or line.startswith(f"{env_key} ="):
            lines[i] = f'{env_key}="{value}"' if value else f"{env_key}="
            return

    if value:
        lines.append(f'{env_key}="{value}"')


ai_settings_service = AISettingsService()
