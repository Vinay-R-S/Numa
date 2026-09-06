"""
AI Settings Router - HTTP only (NUMA-119 P5, PLAN 2.1).

Provider validation, encryption and the integration-key `.env` handling live in
`AISettingsService`; this module parses the request, delegates, and maps the
domain errors to status codes.

Two different scopes share this router (NUMA-125 P6, PLAN 8). The bare
`/ai-settings` routes are per-user and stay open to every signed-in user: that
is the BYOK path, where each user picks a provider/model and stores their own
encrypted API key. `/integration-keys` is server-wide - it rewrites the server
`.env` and mutates `os.environ` for every user at once - so the write side takes
`require_admin`. The read side stays authenticated-only: it answers with one
boolean per key plus non-secret values (file paths, the LeetCode username), so
gating it would break the panel for non-admins without hiding a secret.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.dependencies import get_current_user, require_admin
from .schemas import AISettingsResponse, AISettingsUpdate, ProvidersListResponse
from .service import (
    AISettingsError,
    AISettingsSaveError,
    AISettingsService,
    ai_settings_service,
)

# Mounted at both /ai-settings and /api/ai-settings (main.py alias).
router = APIRouter(prefix="/ai-settings", tags=["ai-settings"])


def get_ai_settings_service() -> AISettingsService:
    return ai_settings_service


def _require_user_id(current_user: dict) -> str:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")
    return user_id


@router.get("", response_model=ProvidersListResponse)
def get_settings(
    current_user: dict = Depends(get_current_user),
    service: AISettingsService = Depends(get_ai_settings_service),
):
    return service.get_settings(_require_user_id(current_user))


@router.put("", response_model=AISettingsResponse)
def update_settings(
    body: AISettingsUpdate,
    current_user: dict = Depends(get_current_user),
    service: AISettingsService = Depends(get_ai_settings_service),
):
    user_id = _require_user_id(current_user)
    try:
        return service.update_settings(user_id, body)
    except AISettingsError as exc:
        raise HTTPException(400, str(exc)) from exc
    except AISettingsSaveError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.delete("", status_code=204)
def delete_settings(
    current_user: dict = Depends(get_current_user),
    service: AISettingsService = Depends(get_ai_settings_service),
):
    """Reset to env-var defaults by removing the user's AI settings row."""
    service.reset_settings(_require_user_id(current_user))


@router.get("/integration-keys")
def get_integration_keys(
    current_user: dict = Depends(get_current_user),
    service: AISettingsService = Depends(get_ai_settings_service),
):
    """Return which integration keys are configured (True/False).
    Non-secret values (like leetcode_username) are also returned as *_value."""
    return service.read_integration_keys()


@router.put("/integration-keys")
def update_integration_keys(
    body: dict,
    current_user: dict = Depends(require_admin),
    service: AISettingsService = Depends(get_ai_settings_service),
):
    """Update integration keys in the server .env file. Admin only."""
    try:
        return service.update_integration_keys(body)
    except AISettingsSaveError as exc:
        # A rejected value is the caller's mistake, not a server fault
        # (NUMA-142 P6, PLAN 8).
        raise HTTPException(400, str(exc)) from exc
