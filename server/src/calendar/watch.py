"""Google Calendar push-notification channel (NUMA-114 P4, NUMA-131 P6,
PLAN 16.1 / 18 / 8).

Owns the watch channel state, the webhook validation and the SSE version feed
that the frontend subscribes to. Moved out of `router.py` so the HTTP layer
holds no Google API calls and no module state.

`/calendar/webhooks/google-calendar` has no JWT - Google calls it - so the
channel token is its authentication. NUMA-131 made that check mandatory. It used
to run only `if WATCH_WEBHOOK_TOKEN`, and when that variable was unset (it is
undocumented, and unset everywhere in this repo) `start_watch` registered the
channel with a throwaway `uuid4` that nothing ever compared. Every guard in the
handler was conditional, so all three collapsed together and any anonymous POST
bumped the version, making every connected browser refetch the month from the
Google Calendar API.
"""
import asyncio
import hmac
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import HTTPException

from .config import GOOGLE_WEBHOOK_BASE_URL, WATCH_WEBHOOK_TOKEN, WEBHOOK_TOKEN_ENV
from .google_auth import get_calendar_service

log = logging.getLogger(__name__)

WEBHOOK_PATH = "/calendar/webhooks/google-calendar"
STREAM_POLL_SECONDS = 8

watch_state: dict[str, str | None] = {
    "channel_id": None,
    "resource_id": None,
    "expiration": None,
    "last_message_number": None,
    # The token this process registered with Google. Never leaves the server:
    # `get_watch_state` builds its response field by field and does not read it.
    "token": None,
}
watch_version = 0

#: Set once the per-process-token warning has been logged. The calendar page
#: registers a watch on every mount, so this would otherwise repeat per visit.
_ephemeral_token_logged = False


def _touch_watch_version() -> None:
    global watch_version
    watch_version += 1


def current_watch_version() -> int:
    return watch_version


def _parse_google_expiration(expiration_ms: str | None) -> str | None:
    if not expiration_ms:
        return None

    try:
        return datetime.fromtimestamp(int(expiration_ms) / 1000).isoformat()
    except (TypeError, ValueError):
        return None


def get_watch_state() -> dict:
    return {
        "active": bool(watch_state.get("channel_id") and watch_state.get("resource_id")),
        "channel_id": watch_state.get("channel_id"),
        "resource_id": watch_state.get("resource_id"),
        "expiration": watch_state.get("expiration"),
    }


def start_watch(user_id: str | None) -> dict:
    """
    Register a Google push channel for the user's primary calendar.

    Returns an inactive result (no exception) when no public callback base URL
    is configured, which is the normal local/dev case.
    """
    global _ephemeral_token_logged

    callback_base = GOOGLE_WEBHOOK_BASE_URL.strip()
    if not callback_base:
        return {"success": False, "channel_id": None, "resource_id": None, "expiration": None}

    callback_url = f"{callback_base.rstrip('/')}{WEBHOOK_PATH}"
    channel_id = str(uuid.uuid4())
    token = WATCH_WEBHOOK_TOKEN or str(uuid.uuid4())
    if not WATCH_WEBHOOK_TOKEN and not _ephemeral_token_logged:
        _ephemeral_token_logged = True
        log.warning(
            "%s is not set; this watch uses a per-process token, so notifications "
            "are refused after a restart until the calendar page registers a new "
            "channel, and refused outright when another worker receives them. Set "
            "it to a fixed secret in production.",
            WEBHOOK_TOKEN_ENV,
        )

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

    expiration = _parse_google_expiration(response.get("expiration"))
    watch_state["channel_id"] = response.get("id")
    watch_state["resource_id"] = response.get("resourceId")
    watch_state["expiration"] = expiration
    watch_state["last_message_number"] = None
    # Registering the token without keeping it was the NUMA-131 bug: the handler
    # had nothing to compare against and waved the notification through.
    watch_state["token"] = token

    return {
        "success": True,
        "channel_id": response.get("id", channel_id),
        "resource_id": response.get("resourceId", ""),
        "expiration": expiration,
    }


def handle_webhook_notification(
    channel_id: str | None,
    resource_id: str | None,
    message_number: str | None,
    token: str | None,
) -> None:
    """Validate a Google push notification and bump the SSE version.

    The token is mandatory: a notification that cannot be matched against a token
    this process registered, or against the configured one, is refused. The
    channel and resource ids stay conditional on being known, so a configured
    fixed token still verifies notifications for a channel registered before a
    restart.
    """
    expected_token = WATCH_WEBHOOK_TOKEN or watch_state.get("token") or ""
    if not expected_token:
        log.warning(
            "Calendar webhook refused: no watch is registered and %s is unset",
            WEBHOOK_TOKEN_ENV,
        )
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    if not hmac.compare_digest((token or "").encode("utf-8"), expected_token.encode("utf-8")):
        log.warning("Calendar webhook refused: token mismatch")
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    if watch_state.get("channel_id") and channel_id != watch_state.get("channel_id"):
        raise HTTPException(status_code=400, detail="Unknown channel id")

    if watch_state.get("resource_id") and resource_id != watch_state.get("resource_id"):
        raise HTTPException(status_code=400, detail="Unknown resource id")

    if message_number and message_number != watch_state.get("last_message_number"):
        watch_state["last_message_number"] = message_number
        _touch_watch_version()


async def stream_calendar_updates() -> AsyncGenerator[str, None]:
    """
    SSE feed: emits a `calendar-updated` frame whenever the version moves.

    Frames use real newlines. The previous implementation escaped them
    (`\\n` in the source), so every frame was one physical line, EventSource
    never saw a frame terminator, and the client listener never fired.
    """
    local_version = current_watch_version()

    while True:
        if local_version != current_watch_version():
            local_version = current_watch_version()
            yield f'event: calendar-updated\ndata: {{"version": {local_version}}}\n\n'

        yield "event: keepalive\ndata: ping\n\n"
        await asyncio.sleep(STREAM_POLL_SECONDS)
