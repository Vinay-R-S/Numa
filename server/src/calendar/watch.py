"""Google Calendar push-notification channel (NUMA-114 P4, NUMA-131/132 P6,
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

The version feed is per user since NUMA-132. One global counter meant any user
creating an event woke every other user's tab into a full month refetch against
the Google API - the scoping half the NUMA-114 note deferred. Each bump now names
the user whose calendar moved: the acting user for a local mutation, and for a
push notification the user whose channel `start_watch` registered.

Channels are a registry keyed by channel id since NUMA-142, not one record.
Several users hold live channels at once, `/watch/status` answers with the
caller's own, and registering a new channel stops the one it replaces. A
notification for a channel this process does not know is refused: the earlier
note here claimed a configured fixed token still verified a channel registered
before a restart, but that path skipped both id guards and bumped the
empty-string version bucket, so the real owner's stream never moved. Surviving a
restart or a second worker needs the `cal_watch_channels` table, which exists
with no writer and no column for the token.
"""
import asyncio
import hmac
import logging
import threading
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import HTTPException

from .config import GOOGLE_WEBHOOK_BASE_URL, WATCH_WEBHOOK_TOKEN, WEBHOOK_TOKEN_ENV
from .google_auth import get_calendar_service

log = logging.getLogger(__name__)

WEBHOOK_PATH = "/calendar/webhooks/google-calendar"
STREAM_POLL_SECONDS = 8

#: Registered push channels, keyed by the channel id Google echoes back.
#: This was a single module-level record, so the second user to open the
#: calendar overwrote the first user's channel: Google kept pushing on the old
#: one, every notification was refused with "Unknown channel id", and Google
#: eventually tore it down. Only one user per process could have a working
#: channel, and `/watch/status` returned whoever registered last to whoever
#: asked (NUMA-142 P6, PLAN 7 / 8).
#:
#: Each entry holds `resource_id`, `expiration`, `last_message_number`, the
#: `token` this process registered (never leaves the server), and the `user_id`
#: whose calendar it watches, so a notification bumps that user's feed alone.
#:
#: Still per-process. A channel registered before a restart, or by another
#: worker, is not in this map and its notifications are refused until the page
#: registers a new one. Surviving that needs the `cal_watch_channels` table,
#: which exists but has no writer and no column for the token.
_watch_channels: dict[str, dict] = {}

#: Guards the registry. Sync routes run in a threadpool.
_channels_lock = threading.Lock()

#: Per-user version counters. A token with no `sub` claim keys on "", which keeps
#: it out of every real user's bucket; such callers share that one bucket, which
#: costs nothing because `create_jwt` always sets `sub`.
watch_versions: dict[str, int] = {}

#: Sync routes run in a threadpool, so `+= 1` on a shared dict is not atomic.
_version_lock = threading.Lock()

#: Set once the per-process-token warning has been logged. The calendar page
#: registers a watch on every mount, so this would otherwise repeat per visit.
_ephemeral_token_logged = False


def _version_key(user_id: str | None) -> str:
    return user_id or ""


def _touch_watch_version(user_id: str | None) -> None:
    """Bump one user's feed. The parameter is required: a bump with no owner is
    the bug NUMA-132 fixed, not a default worth keeping."""
    key = _version_key(user_id)
    with _version_lock:
        watch_versions[key] = watch_versions.get(key, 0) + 1


def current_watch_version(user_id: str | None) -> int:
    return watch_versions.get(_version_key(user_id), 0)


def _parse_google_expiration(expiration_ms: str | None) -> str | None:
    if not expiration_ms:
        return None

    try:
        return datetime.fromtimestamp(int(expiration_ms) / 1000).isoformat()
    except (TypeError, ValueError):
        return None


def _user_channel(user_id: str | None) -> tuple[str | None, dict | None]:
    """This user's registered channel, or (None, None)."""
    key = _version_key(user_id)
    with _channels_lock:
        for channel_id, entry in _watch_channels.items():
            if _version_key(entry.get("user_id")) == key:
                return channel_id, dict(entry)
    return None, None


def get_watch_state(user_id: str | None) -> dict:
    """The caller's own channel. Takes a user id because it used to answer with
    the process-global record: whoever registered last, including their channel
    and resource ids, returned to anyone who asked, and reported `active` to a
    user who had no channel at all."""
    channel_id, entry = _user_channel(user_id)
    if not entry:
        return {"active": False, "channel_id": None, "resource_id": None, "expiration": None}

    return {
        "active": bool(channel_id and entry.get("resource_id")),
        "channel_id": channel_id,
        "resource_id": entry.get("resource_id"),
        "expiration": entry.get("expiration"),
    }


def _stop_channel(service, channel_id: str, resource_id: str | None) -> None:
    """Ask Google to stop a channel we are about to replace.

    The calendar page registers on every mount, so without this each visit left
    another live channel pointed at the same webhook. They no longer matched the
    registry, so every notification they delivered was refused, Google retried
    each with backoff, and the per-calendar channel quota drained.
    """
    if not channel_id or not resource_id:
        return
    try:
        service.channels().stop(body={"id": channel_id, "resourceId": resource_id}).execute()
    except Exception:
        log.debug("Could not stop calendar channel %s", channel_id, exc_info=True)


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

    # Replace this user's own channel, and only theirs.
    previous_id, previous = _user_channel(user_id)
    if previous_id:
        _stop_channel(service, previous_id, previous.get("resource_id"))
        with _channels_lock:
            _watch_channels.pop(previous_id, None)

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
    registered_id = response.get("id") or channel_id
    with _channels_lock:
        _watch_channels[registered_id] = {
            "resource_id": response.get("resourceId"),
            "expiration": expiration,
            "last_message_number": None,
            # Registering the token without keeping it was the NUMA-131 bug: the
            # handler had nothing to compare against and waved notifications
            # through.
            "token": token,
            "user_id": user_id,
        }

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

    The channel id selects which registration to check against, because several
    users can hold channels at once. The token is then mandatory and compared
    against the token that channel was registered with.

    A channel this process does not know is refused rather than waved through.
    Previously an unknown channel skipped both id guards and bumped
    `_version_key(None)` - the empty-string bucket - so after a restart the
    real owner's stream never moved and the notification was silently lost. A
    refused channel is one Google eventually stops, and the calendar page
    registers a fresh one on its next mount.
    """
    with _channels_lock:
        entry = dict(_watch_channels.get(channel_id or "", {}))

    if not entry:
        log.warning("Calendar webhook refused: unknown channel %r", channel_id)
        raise HTTPException(status_code=400, detail="Unknown channel id")

    expected_token = entry.get("token") or WATCH_WEBHOOK_TOKEN or ""
    if not expected_token:
        log.warning(
            "Calendar webhook refused: no token registered for the channel and %s is unset",
            WEBHOOK_TOKEN_ENV,
        )
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    if not hmac.compare_digest((token or "").encode("utf-8"), expected_token.encode("utf-8")):
        log.warning("Calendar webhook refused: token mismatch")
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    if entry.get("resource_id") and resource_id != entry.get("resource_id"):
        raise HTTPException(status_code=400, detail="Unknown resource id")

    if message_number and message_number != entry.get("last_message_number"):
        with _channels_lock:
            live = _watch_channels.get(channel_id or "")
            if live is not None:
                live["last_message_number"] = message_number
        _touch_watch_version(entry.get("user_id"))


async def stream_calendar_updates(user_id: str | None) -> AsyncGenerator[str, None]:
    """
    SSE feed for one user: emits `calendar-updated` when their version moves.

    Frames use real newlines. The previous implementation escaped them
    (`\\n` in the source), so every frame was one physical line, EventSource
    never saw a frame terminator, and the client listener never fired.
    """
    local_version = current_watch_version(user_id)

    while True:
        if local_version != current_watch_version(user_id):
            local_version = current_watch_version(user_id)
            yield f'event: calendar-updated\ndata: {{"version": {local_version}}}\n\n'

        yield "event: keepalive\ndata: ping\n\n"
        await asyncio.sleep(STREAM_POLL_SECONDS)
