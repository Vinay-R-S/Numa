import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from typing import AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from jose import JWTError, jwt

from ..auth.dependencies import get_current_user
from .schemas import (
    CalendarEvent,
    CalendarEventUpsert,
    DeleteResponse,
    EventsResponse,
    OAuthStartResponse,
    OAuthStatusResponse,
    WatchStartResponse,
    WatchStateResponse,
)
from .service import (
    build_google_oauth_authorization_url,
    create_event_from_payload,
    delete_event_by_id,
    exchange_google_oauth_code,
    get_calendar_service,
    get_events_for_frontend,
    has_calendar_credentials,
    update_event_from_payload,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])

WATCH_WEBHOOK_TOKEN = os.getenv("WATCH_WEBHOOK_TOKEN", "")
GOOGLE_WEBHOOK_BASE_URL = os.getenv("GOOGLE_WEBHOOK_BASE_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/calendar/oauth/callback")
GOOGLE_OAUTH_SUCCESS_REDIRECT = os.getenv(
    "GOOGLE_OAUTH_SUCCESS_REDIRECT",
    f"{os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')}/calendar",
)

watch_state: Dict[str, Optional[str]] = {
    "channel_id": None,
    "resource_id": None,
    "expiration": None,
    "last_message_number": None,
}
watch_version = 0
# Calendar always fetches the full current month (no configurable window needed)


def _touch_watch_version() -> None:
    global watch_version
    watch_version += 1


def _parse_google_expiration(expiration_ms: Optional[str]) -> Optional[str]:
    if not expiration_ms:
        return None

    try:
        expiration_int = int(expiration_ms)
        return datetime.fromtimestamp(expiration_int / 1000).isoformat()
    except (TypeError, ValueError):
        return None


def _is_calendar_not_connected_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "google calendar is not connected" in msg
        or "session expired" in msg
        or "please reconnect" in msg
    )


def _build_oauth_state(user_id: str) -> str:
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "scope": "google_calendar_oauth",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_oauth_state(state: str) -> str:
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")

    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc

    if payload.get("scope") != "google_calendar_oauth":
        raise HTTPException(status_code=400, detail="Invalid OAuth state scope")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="OAuth state is missing user id")

    return str(user_id)


def _oauth_redirect(status: str, reason: Optional[str] = None) -> RedirectResponse:
    separator = "&" if "?" in GOOGLE_OAUTH_SUCCESS_REDIRECT else "?"
    target = f"{GOOGLE_OAUTH_SUCCESS_REDIRECT}{separator}google_oauth={quote_plus(status)}"
    if reason:
        target = f"{target}&reason={quote_plus(reason)}"
    return RedirectResponse(url=target, status_code=302)


@router.get("/oauth/status", response_model=OAuthStatusResponse)
def oauth_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="User session is invalid")

    return OAuthStatusResponse(connected=has_calendar_credentials(user_id))


@router.get("/token/health")
def token_health(current_user: dict = Depends(get_current_user)):
    """
    Actively validate the stored Google Calendar token by making a real API call.
    Returns a JSON object so the frontend can decide whether to prompt re-auth.

    Response shape:
      { "valid": true,  "connected": true }        – token exists and works
      { "valid": false, "connected": true,          – token file exists but is expired/revoked
        "reason": "...", "reconnect_url": "..." }
      { "valid": false, "connected": false }        – no token file at all
    """
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="User session is invalid")

    file_exists = has_calendar_credentials(user_id)

    if not file_exists:
        return {"valid": False, "connected": False}

    # Attempt a real API call to verify the token is still accepted by Google
    try:
        svc = get_calendar_service(user_id=user_id)
        svc.calendarList().list(maxResults=1).execute()
        return {"valid": True, "connected": True}
    except RuntimeError as exc:
        # Token exists but is expired/revoked — generate a fresh OAuth URL
        try:
            state = _build_oauth_state(user_id)
            reconnect_url = build_google_oauth_authorization_url(
                redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
                state=state,
            )
        except Exception:
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

@router.post("/oauth/start", response_model=OAuthStartResponse)
def oauth_start(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="User session is invalid")

    try:
        state = _build_oauth_state(user_id)
        authorization_url = build_google_oauth_authorization_url(
            redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
            state=state,
        )
        return OAuthStartResponse(authorization_url=authorization_url)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start Google OAuth: {exc}") from exc


@router.get("/oauth/callback")
def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    if error:
        return _oauth_redirect("error", error)
    if not code or not state:
        return _oauth_redirect("error", "Missing OAuth code/state")

    try:
        user_id = _decode_oauth_state(state)
        exchange_google_oauth_code(user_id=user_id, code=code, redirect_uri=GOOGLE_OAUTH_REDIRECT_URI)
        _touch_watch_version()
        return _oauth_redirect("connected")
    except HTTPException as exc:
        return _oauth_redirect("error", str(exc.detail))
    except Exception as exc:
        return _oauth_redirect("error", str(exc))


@router.get("/events", response_model=EventsResponse)
def get_events(
    refresh: bool = Query(False, description="Force re-fetch from Google API, bypassing the 30-min DB cache"),
    current_user: dict = Depends(get_current_user),
):
    """Return all events for the current calendar month (holidays & birthdays included).

    By default, events are served from the DB cache if last synced within 30 minutes.
    Pass ?refresh=true to force a fresh fetch from Google Calendar.
    """
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    try:
        events = get_events_for_frontend(user_id=user_id, force_refresh=refresh)
        return EventsResponse(events=events)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        if _is_calendar_not_connected_error(exc):
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {exc}") from exc


@router.post("/events", response_model=CalendarEvent)
def create_event(payload: CalendarEventUpsert, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    try:
        created = create_event_from_payload(payload, user_id=user_id)
        _touch_watch_version()
        return CalendarEvent(**created)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        if _is_calendar_not_connected_error(exc):
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail=f"Failed to create event: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create event: {exc}") from exc


@router.put("/events/{event_id}", response_model=CalendarEvent)
def update_event(
    event_id: str,
    payload: CalendarEventUpsert,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    try:
        updated = update_event_from_payload(event_id, payload, user_id=user_id)
        _touch_watch_version()
        return CalendarEvent(**updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        if _is_calendar_not_connected_error(exc):
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail=f"Failed to update event: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update event: {exc}") from exc


@router.delete("/events/{event_id}", response_model=DeleteResponse)
def delete_event(event_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    try:
        delete_event_by_id(event_id, user_id=user_id)
        _touch_watch_version()
        return DeleteResponse(success=True)
    except RuntimeError as exc:
        if _is_calendar_not_connected_error(exc):
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {exc}") from exc


@router.get("/watch/status", response_model=WatchStateResponse)
def watch_status(current_user: dict = Depends(get_current_user)):
    _ = current_user
    return WatchStateResponse(
        active=bool(watch_state.get("channel_id") and watch_state.get("resource_id")),
        channel_id=watch_state.get("channel_id"),
        resource_id=watch_state.get("resource_id"),
        expiration=watch_state.get("expiration"),
    )


@router.post("/watch/start", response_model=WatchStartResponse)
def start_calendar_watch(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None

    callback_base = GOOGLE_WEBHOOK_BASE_URL.strip()
    if not callback_base:
        return WatchStartResponse(
            success=False,
            channel_id=None,
            resource_id=None,
            expiration=None,
        )

    callback_url = f"{callback_base.rstrip('/')}/calendar/webhooks/google-calendar"
    channel_id = str(uuid.uuid4())
    token = WATCH_WEBHOOK_TOKEN or str(uuid.uuid4())

    try:
        service = get_calendar_service(user_id=user_id)
        response = (
            service.events()
            .watch(
                calendarId="primary",
                body={
                    "id": channel_id,
                    "type": "web_hook",
                    "address": callback_url,
                    "token": token,
                },
            )
            .execute()
        )

        watch_state["channel_id"] = response.get("id")
        watch_state["resource_id"] = response.get("resourceId")
        watch_state["expiration"] = _parse_google_expiration(response.get("expiration"))
        watch_state["last_message_number"] = None

        return WatchStartResponse(
            success=True,
            channel_id=response.get("id", channel_id),
            resource_id=response.get("resourceId", ""),
            expiration=_parse_google_expiration(response.get("expiration")),
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        if _is_calendar_not_connected_error(exc):
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail=f"Failed to start watch: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start watch: {exc}") from exc


@router.post("/webhooks/google-calendar")
async def google_calendar_webhook(request: Request):
    channel_id = request.headers.get("X-Goog-Channel-Id")
    resource_id = request.headers.get("X-Goog-Resource-Id")
    message_number = request.headers.get("X-Goog-Message-Number")
    token = request.headers.get("X-Goog-Channel-Token", "")

    if WATCH_WEBHOOK_TOKEN and token != WATCH_WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    if watch_state.get("channel_id") and channel_id != watch_state.get("channel_id"):
        raise HTTPException(status_code=400, detail="Unknown channel id")

    if watch_state.get("resource_id") and resource_id != watch_state.get("resource_id"):
        raise HTTPException(status_code=400, detail="Unknown resource id")

    if message_number and message_number != watch_state.get("last_message_number"):
        watch_state["last_message_number"] = message_number
        _touch_watch_version()

    return {"ok": True}


@router.get("/events/stream")
async def stream_event_updates():
    async def event_generator() -> AsyncGenerator[str, None]:
        local_version = watch_version

        while True:
            if local_version != watch_version:
                local_version = watch_version
                yield f"event: calendar-updated\\ndata: {{\"version\": {watch_version}}}\\n\\n"

            yield "event: keepalive\\ndata: ping\\n\\n"
            await asyncio.sleep(8)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
