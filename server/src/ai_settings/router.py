"""
AI Settings Router - CRUD endpoints for per-user LLM provider/model config.
"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..auth.dependencies import get_current_user
from ..db import _get_conn
from ..llm_factory import (
    encrypt_api_key,
    get_available_providers,
    PROVIDER_MODELS,
    DEFAULT_MODELS,
)
from .schemas import (
    AISettingsUpdate,
    AISettingsResponse,
    ProviderInfo,
    ProvidersListResponse,
)

router = APIRouter(prefix="/api/ai-settings", tags=["ai-settings"])


def _row_to_response(row, description) -> AISettingsResponse:
    d = {col.name: val for col, val in zip(description, row)}
    return AISettingsResponse(
        provider=d["provider"],
        model_id=d["model_id"],
        has_api_key=bool(d.get("encrypted_api_key")),
        ollama_base_url=d.get("ollama_base_url"),
        temperature=d.get("temperature", 0.1),
    )


@router.get("", response_model=ProvidersListResponse)
def get_settings(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    providers = [ProviderInfo(**p) for p in get_available_providers()]

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT provider, model_id, encrypted_api_key, ollama_base_url, temperature
            FROM public.user_ai_settings
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
        current = _row_to_response(row, cur.description) if row else None
        cur.close()
    finally:
        conn.close()

    return ProvidersListResponse(providers=providers, current=current)


@router.put("", response_model=AISettingsResponse)
def update_settings(
    body: AISettingsUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    if body.provider not in PROVIDER_MODELS:
        raise HTTPException(400, f"Unsupported provider: {body.provider}")

    if body.model_id not in PROVIDER_MODELS[body.provider]:
        raise HTTPException(
            400,
            f"Model '{body.model_id}' not available for {body.provider}. "
            f"Choose from: {PROVIDER_MODELS[body.provider]}",
        )

    encrypted = None
    if body.api_key and body.api_key.strip():
        encrypted = encrypt_api_key(body.api_key.strip())

    conn = _get_conn()
    try:
        cur = conn.cursor()

        if encrypted:
            cur.execute(
                """
                INSERT INTO public.user_ai_settings
                    (user_id, provider, model_id, encrypted_api_key, ollama_base_url, temperature)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    provider          = EXCLUDED.provider,
                    model_id          = EXCLUDED.model_id,
                    encrypted_api_key = EXCLUDED.encrypted_api_key,
                    ollama_base_url   = EXCLUDED.ollama_base_url,
                    temperature       = EXCLUDED.temperature,
                    updated_at        = NOW()
                RETURNING provider, model_id, encrypted_api_key, ollama_base_url, temperature
                """,
                (user_id, body.provider, body.model_id, encrypted,
                 body.ollama_base_url, body.temperature),
            )
        else:
            cur.execute(
                """
                INSERT INTO public.user_ai_settings
                    (user_id, provider, model_id, ollama_base_url, temperature)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    provider        = EXCLUDED.provider,
                    model_id        = EXCLUDED.model_id,
                    ollama_base_url = EXCLUDED.ollama_base_url,
                    temperature     = EXCLUDED.temperature,
                    updated_at      = NOW()
                RETURNING provider, model_id, encrypted_api_key, ollama_base_url, temperature
                """,
                (user_id, body.provider, body.model_id,
                 body.ollama_base_url, body.temperature),
            )

        row = cur.fetchone()
        result = _row_to_response(row, cur.description)
        conn.commit()
        cur.close()
        return result
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"Failed to save AI settings: {exc}")
    finally:
        conn.close()


@router.delete("", status_code=204)
def delete_settings(current_user: dict = Depends(get_current_user)):
    """Reset to env-var defaults by removing the user's AI settings row."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM public.user_ai_settings WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()


_INTEGRATION_CHECK_KEYS = {
    "GOOGLE_FIT_CLIENT_ID": "google_fit_client_id",
    "GOOGLE_FIT_CLIENT_SECRET": "google_fit_client_secret",
    "SLACK_CLIENT_ID": "slack_client_id",
    "SLACK_CLIENT_SECRET": "slack_client_secret",
    "SLACK_BOT_TOKEN": "slack_bot_token",
    "GITHUB_CLIENT_ID": "github_client_id",
    "GITHUB_CLIENT_SECRET": "github_client_secret",
    "LEETCODE_USERNAME": "leetcode_username",
    "STRAVA_CLIENT_ID": "strava_client_id",
    "STRAVA_CLIENT_SECRET": "strava_client_secret",
}

_INTEGRATION_ALLOWED_KEYS = {
    "google_fit_client_id": "GOOGLE_FIT_CLIENT_ID",
    "google_fit_client_secret": "GOOGLE_FIT_CLIENT_SECRET",
    "slack_client_id": "SLACK_CLIENT_ID",
    "slack_client_secret": "SLACK_CLIENT_SECRET",
    "slack_bot_token": "SLACK_BOT_TOKEN",
    "github_client_id": "GITHUB_CLIENT_ID",
    "github_client_secret": "GITHUB_CLIENT_SECRET",
    "leetcode_username": "LEETCODE_USERNAME",
    "strava_client_id": "STRAVA_CLIENT_ID",
    "strava_client_secret": "STRAVA_CLIENT_SECRET",
}


@router.get("/integration-keys")
def get_integration_keys(current_user: dict = Depends(get_current_user)):
    """Return which integration keys are configured (True/False).
    Non-secret values (like leetcode_username) are also returned as *_value."""
    keys_status: dict = {}
    for env_key, api_key in _INTEGRATION_CHECK_KEYS.items():
        val = os.getenv(env_key, "")
        keys_status[api_key] = bool(val and val.strip())

    # Expose non-secret values so the frontend can use them directly
    lc = os.getenv("LEETCODE_USERNAME", "").strip()
    if lc:
        keys_status["leetcode_username_value"] = lc

    return keys_status


@router.put("/integration-keys")
def update_integration_keys(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Update integration keys in the server .env file."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"

    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    updated_keys: set[str] = set()
    for api_key, value in body.items():
        if api_key not in _INTEGRATION_ALLOWED_KEYS:
            continue
        env_key = _INTEGRATION_ALLOWED_KEYS[api_key]
        if not isinstance(value, str):
            continue

        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{env_key}=") or line.startswith(f"{env_key} ="):
                lines[i] = f'{env_key}="{value}"' if value else f"{env_key}="
                found = True
                break
        if not found and value:
            lines.append(f'{env_key}="{value}"')

        os.environ[env_key] = value
        updated_keys.add(api_key)

    env_path.write_text("\n".join(lines) + "\n")

    return {"ok": True, "updated": list(updated_keys)}
