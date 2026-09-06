"""AI settings business logic (NUMA-119 P5, PLAN 2.1 / 5.2 / 21.1).

Provider/model validation, API-key encryption, the response mapping and the
integration-key env-file handling were extracted verbatim from `router.py`,
which is now HTTP-only. Behavior is unchanged: the same messages, the same
`.env` rewrite rules and the same response shapes.
"""
from __future__ import annotations

import os

from ..core.base import BaseService
from ..core.llm_factory import PROVIDER_MODELS, get_available_providers
from ..core.security import EncryptionKeyError, encrypt_api_key
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
            try:
                encrypted = encrypt_api_key(body.api_key.strip())
            except EncryptionKeyError as exc:
                # Was an unhandled ValueError from Fernet, so saving a key
                # answered a bare 500 with no hint of the cause (NUMA-128).
                raise AISettingsSaveError(f"Cannot store the API key: {exc}") from exc

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
        """Write the known keys into the server `.env` and the live environment.

        Every value is validated before anything is written. A value carrying a
        newline used to produce a truncated quoted line followed by a bare
        `NAME=` line that `load_dotenv` picked up on the next boot, so an admin
        could inject arbitrary settings (a `DATABASE_URL`, say) through an API
        key field; an embedded quote closed the string early and merged two
        settings; and a NUL raised out of `os.environ` after earlier keys had
        already been mutated, leaving the file and the process disagreeing
        (NUMA-142 P6, PLAN 8).
        """
        pending: list[tuple[str, str, str]] = []
        for api_key, value in body.items():
            env_key = INTEGRATION_KEYS.get(api_key)
            if not env_key or not isinstance(value, str):
                continue
            _validate_env_value(api_key, value)
            pending.append((api_key, env_key, value))

        # Nothing recognized in the body: leave the file alone instead of
        # rewriting it, which would normalize its line endings for no reason.
        if not pending:
            return {"ok": True, "updated": []}

        lines: list[str] = []
        if ENV_FILE_PATH.exists():
            lines = ENV_FILE_PATH.read_text().splitlines()

        for _api_key, env_key, value in pending:
            _upsert_env_line(lines, env_key, value)

        ENV_FILE_PATH.write_text("\n".join(lines) + "\n")

        # The process is updated only once the file is written, so a failure
        # cannot leave the two out of step.
        for _api_key, env_key, value in pending:
            os.environ[env_key] = value

        return {"ok": True, "updated": [api_key for api_key, _env, _v in pending]}


# Long enough for any provider token this app stores, short enough that the
# .env cannot be used as a blob store.
_ENV_VALUE_MAX_LENGTH = 512

# Values are written single-quoted, which `load_dotenv` and every POSIX shell
# treat literally, so a Windows path like C:\Users\numa\token.json survives
# intact - three of these keys are file paths, and banning the backslash
# outright rejected them (NUMA-142 P6 review). What cannot be represented
# inside a single-quoted line is a single quote and any control character: a
# newline would start a second setting that the next boot would load.
_FORBIDDEN_ENV_CHARS = (
    {"'"} | {chr(code) for code in range(0x20)} | {chr(0x7F)}
)


def _validate_env_value(api_key: str, value: str) -> None:
    if len(value) > _ENV_VALUE_MAX_LENGTH:
        raise AISettingsSaveError(
            f"{api_key} is too long (max {_ENV_VALUE_MAX_LENGTH} characters)"
        )
    if any(ch in _FORBIDDEN_ENV_CHARS for ch in value):
        raise AISettingsSaveError(
            f"{api_key} may not contain quotes, newlines or control characters"
        )


def _upsert_env_line(lines: list[str], env_key: str, value: str) -> None:
    """Replace the first `KEY=`/`KEY =` line in place, else append a new one."""
    for i, line in enumerate(lines):
        if line.startswith(f"{env_key}=") or line.startswith(f"{env_key} ="):
            lines[i] = _env_line(env_key, value)
            return

    if value:
        lines.append(_env_line(env_key, value))


def _env_line(env_key: str, value: str) -> str:
    """One `KEY='value'` line. Single quotes: dotenv decodes escape sequences
    inside double quotes, which would mangle a Windows path's backslashes."""
    if not value:
        return f"{env_key}="
    return f"{env_key}='{value}'"


ai_settings_service = AISettingsService()
