"""
Calendar Router - HTTP only (NUMA-114 P4, PLAN 2.1 / 18).

Orchestration lives in `CalendarService`; the OAuth flow in `oauth.py`, the
Google push channel and SSE feed in `watch.py`, and env reads in `config.py`.
This module parses requests, delegates through a `Depends`-injected service,
and maps errors to HTTP.

Backward compatibility: `GOOGLE_OAUTH_REDIRECT_URI` and `_build_oauth_state`
stay importable from here (`auth/router.py` uses both).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..auth.dependencies import get_current_user
from . import watch
from .config import (  # noqa: F401
    GOOGLE_OAUTH_REDIRECT_URI,
    GOOGLE_WEBHOOK_BASE_URL,
    WATCH_WEBHOOK_TOKEN,
)
from .google_auth import has_calendar_credentials
from .oauth import (  # noqa: F401
    _build_oauth_state,
    _decode_oauth_state,
    build_authorization_url,
    check_token_health,
    complete_authorization,
    oauth_redirect,
)
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
from .service import CalendarService, calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def get_calendar_feature_service() -> CalendarService:
    return calendar_service


def _require_user_id(current_user: dict) -> str:
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail="User session is invalid")
    return str(user_id)


def _optional_user_id(current_user: dict) -> str | None:
    return current_user.get("sub") if isinstance(current_user, dict) else None


def _is_calendar_not_connected_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "google calendar is not connected" in msg
        or "session expired" in msg
        or "please reconnect" in msg
    )


def _http_error(exc: Exception, action: str) -> HTTPException:
    """Map a service error to 401 (reconnect needed) or 500."""
    if isinstance(exc, RuntimeError) and _is_calendar_not_connected_error(exc):
        return HTTPException(status_code=401, detail=str(exc))
    return HTTPException(status_code=500, detail=f"{action}: {exc}")


@router.get("/oauth/status", response_model=OAuthStatusResponse)
def oauth_status(current_user: dict = Depends(get_current_user)):
    user_id = _require_user_id(current_user)
    return OAuthStatusResponse(connected=has_calendar_credentials(user_id))


@router.get("/token/health")
def token_health(current_user: dict = Depends(get_current_user)):
    """Validate the stored Google token so the UI can prompt for re-auth."""
    return check_token_health(_require_user_id(current_user))


@router.post("/oauth/start", response_model=OAuthStartResponse)
def oauth_start(current_user: dict = Depends(get_current_user)):
    user_id = _require_user_id(current_user)

    try:
        return OAuthStartResponse(authorization_url=build_authorization_url(user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start Google OAuth: {exc}") from exc


@router.get("/oauth/callback")
def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        return oauth_redirect("error", error)
    if not code or not state:
        return oauth_redirect("error", "Missing OAuth code/state")

    try:
        complete_authorization(state, code)
        watch._touch_watch_version()
        return oauth_redirect("connected")
    except HTTPException as exc:
        return oauth_redirect("error", str(exc.detail))
    except Exception as exc:
        return oauth_redirect("error", str(exc))


@router.get("/events", response_model=EventsResponse)
def get_events(
    refresh: bool = Query(False, description="Force re-fetch from Google API, bypassing the 30-min DB cache"),
    current_user: dict = Depends(get_current_user),
    service: CalendarService = Depends(get_calendar_feature_service),
):
    """Return all events for the current calendar month (holidays & birthdays included).

    By default, events are served from the DB cache if last synced within 30 minutes.
    Pass ?refresh=true to force a fresh fetch from Google Calendar.
    """
    try:
        events = service.get_events_for_frontend(
            user_id=_optional_user_id(current_user),
            force_refresh=refresh,
        )
        return EventsResponse(events=events)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, "Failed to fetch events") from exc


@router.post("/events", response_model=CalendarEvent)
def create_event(
    payload: CalendarEventUpsert,
    current_user: dict = Depends(get_current_user),
    service: CalendarService = Depends(get_calendar_feature_service),
):
    try:
        created = service.create_event_from_payload(payload, user_id=_optional_user_id(current_user))
        watch._touch_watch_version()
        return CalendarEvent(**created)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, "Failed to create event") from exc


@router.put("/events/{event_id}", response_model=CalendarEvent)
def update_event(
    event_id: str,
    payload: CalendarEventUpsert,
    current_user: dict = Depends(get_current_user),
    service: CalendarService = Depends(get_calendar_feature_service),
):
    try:
        updated = service.update_event_from_payload(
            event_id, payload, user_id=_optional_user_id(current_user)
        )
        watch._touch_watch_version()
        return CalendarEvent(**updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, "Failed to update event") from exc


@router.delete("/events/{event_id}", response_model=DeleteResponse)
def delete_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    service: CalendarService = Depends(get_calendar_feature_service),
):
    try:
        service.delete_event_by_id(event_id, user_id=_optional_user_id(current_user))
        watch._touch_watch_version()
        return DeleteResponse(success=True)
    except Exception as exc:
        raise _http_error(exc, "Failed to delete event") from exc


@router.get("/watch/status", response_model=WatchStateResponse)
def watch_status(current_user: dict = Depends(get_current_user)):
    _ = current_user
    return WatchStateResponse(**watch.get_watch_state())


@router.post("/watch/start", response_model=WatchStartResponse)
def start_calendar_watch(current_user: dict = Depends(get_current_user)):
    try:
        return WatchStartResponse(**watch.start_watch(_optional_user_id(current_user)))
    except HTTPException:
        raise
    except Exception as exc:
        raise _http_error(exc, "Failed to start watch") from exc


@router.post("/webhooks/google-calendar")
async def google_calendar_webhook(request: Request):
    watch.handle_webhook_notification(
        channel_id=request.headers.get("X-Goog-Channel-Id"),
        resource_id=request.headers.get("X-Goog-Resource-Id"),
        message_number=request.headers.get("X-Goog-Message-Number"),
        token=request.headers.get("X-Goog-Channel-Token", ""),
    )
    return {"ok": True}


@router.get("/events/stream")
async def stream_event_updates():
    return StreamingResponse(
        watch.stream_calendar_updates(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
