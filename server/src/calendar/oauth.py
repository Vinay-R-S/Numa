"""Google Calendar OAuth flow (NUMA-114 P4, PLAN 16.1 / 18).

State signing/verification, the post-callback redirect and the live token
health probe, moved out of `router.py` so the HTTP layer stops calling the
Google API directly. Behavior is unchanged, including the HTTPException status
codes and the shape of the token-health payload.
"""
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import quote_plus

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from .config import (
    GOOGLE_OAUTH_REDIRECT_URI,
    GOOGLE_OAUTH_SUCCESS_REDIRECT,
    JWT_ALGORITHM,
    JWT_SECRET,
)
from .google_auth import (
    build_google_oauth_authorization_url,
    exchange_google_oauth_code,
    get_calendar_service,
    has_calendar_credentials,
)

log = logging.getLogger(__name__)

OAUTH_STATE_SCOPE = "google_calendar_oauth"
OAUTH_STATE_TTL_MINUTES = 10


def _build_oauth_state(user_id: str) -> str:
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")

    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "scope": OAUTH_STATE_SCOPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=OAUTH_STATE_TTL_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_oauth_state(state: str) -> str:
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")

    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc

    if payload.get("scope") != OAUTH_STATE_SCOPE:
        raise HTTPException(status_code=400, detail="Invalid OAuth state scope")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="OAuth state is missing user id")

    return str(user_id)


def oauth_redirect(status: str, reason: str | None = None) -> RedirectResponse:
    separator = "&" if "?" in GOOGLE_OAUTH_SUCCESS_REDIRECT else "?"
    target = f"{GOOGLE_OAUTH_SUCCESS_REDIRECT}{separator}google_oauth={quote_plus(status)}"
    if reason:
        target = f"{target}&reason={quote_plus(reason)}"
    return RedirectResponse(url=target, status_code=302)


def build_authorization_url(user_id: str) -> str:
    """Signed-state authorization URL for the connect button."""
    state = _build_oauth_state(user_id)
    return build_google_oauth_authorization_url(
        redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
        state=state,
    )


def complete_authorization(state: str, code: str) -> str:
    """Verify the state, exchange the code, and return the owning user id."""
    user_id = _decode_oauth_state(state)
    exchange_google_oauth_code(user_id=user_id, code=code, redirect_uri=GOOGLE_OAUTH_REDIRECT_URI)
    return user_id


def check_token_health(user_id: str) -> dict:
    """
    Actively validate the stored Google Calendar token with a real API call.

      {"valid": True,  "connected": True}                              token works
      {"valid": False, "connected": True, "reason", "reconnect_url"}   expired/revoked
      {"valid": False, "connected": False}                             no token stored
    """
    if not has_calendar_credentials(user_id):
        return {"valid": False, "connected": False}

    try:
        service = get_calendar_service(user_id=user_id)
        service.calendarList().list(maxResults=1).execute()
        return {"valid": True, "connected": True}
    except RuntimeError as exc:
        # Token exists but is expired/revoked - offer a fresh OAuth URL.
        try:
            reconnect_url = build_authorization_url(user_id)
        except Exception as url_exc:
            log.warning("Could not build calendar reconnect URL: %s", url_exc)
            reconnect_url = None
        return {
            "valid": False,
            "connected": True,
            "reason": str(exc),
            "reconnect_url": reconnect_url,
        }
    except Exception as exc:
        return {
            "valid": False,
            "connected": True,
            "reason": f"Unexpected error: {exc}",
            "reconnect_url": None,
        }
