import logging
from typing import Dict, Iterable, Optional

log = logging.getLogger(__name__)

_TRANSIENT_ERROR_MARKERS = (
    "getaddrinfo failed",
    "could not translate host name",
    "name or service not known",
    "temporary failure in name resolution",
    "unable to find the server",
    "server closed the connection unexpectedly",
    "connection unexpectedly",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
)


def _is_transient_dependency_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_ERROR_MARKERS)


def _dependency_unavailable_detail(service: str) -> str:
    return f"{service} temporarily unavailable; sync skipped"


def _log_sync_exception(message: str, exc: Exception, *args) -> None:
    if _is_transient_dependency_error(exc):
        log.debug(message, *args, exc)
    else:
        log.warning(message, *args, exc)


def fetch_latest_for_user(user_id: str) -> Dict:
    """Fetch latest external app data for one NUMA user."""
    result = {
        "user_id": user_id,
        "calendar": {"ok": True, "fetched": 0, "detail": "not connected"},
        "slack": {"ok": True, "fetched": 0, "channels": 0, "detail": "not connected"},
        "health": {"ok": True, "detail": "not synced"},
        "github": {"ok": True, "detail": "not connected"},
    }

    try:
        from src.calendar.service import get_events_for_frontend

        events = get_events_for_frontend(user_id=user_id, force_refresh=True)
        result["calendar"] = {
            "ok": True,
            "fetched": len(events),
            "detail": "Calendar fetch complete",
        }
    except Exception as exc:
        _log_sync_exception("Calendar fetch failed for user %s: %s", exc, user_id)
        detail = _dependency_unavailable_detail("Calendar") if _is_transient_dependency_error(exc) else str(exc)
        result["calendar"] = {"ok": False, "fetched": 0, "detail": detail}

    try:
        from src.slack_agent.router import fetch_latest_slack_for_user

        result["slack"] = fetch_latest_slack_for_user(user_id)
    except Exception as exc:
        _log_sync_exception("Slack fetch failed for user %s: %s", exc, user_id)
        detail = _dependency_unavailable_detail("Slack") if _is_transient_dependency_error(exc) else str(exc)
        result["slack"] = {"ok": False, "fetched": 0, "channels": 0, "detail": detail}

    try:
        from src.health_agent.router import sync_health_for_user

        result["health"] = sync_health_for_user(user_id)
    except Exception as exc:
        _log_sync_exception("Health sync failed for user %s: %s", exc, user_id)
        detail = _dependency_unavailable_detail("Health") if _is_transient_dependency_error(exc) else str(exc)
        result["health"] = {"ok": False, "detail": detail}

    try:
        from src.github_agent.router import fetch_and_store_github_stats_for_user

        result["github"] = fetch_and_store_github_stats_for_user(user_id)
    except Exception as exc:
        _log_sync_exception("GitHub sync failed for user %s: %s", exc, user_id)
        detail = _dependency_unavailable_detail("GitHub") if _is_transient_dependency_error(exc) else str(exc)
        result["github"] = {"ok": False, "detail": detail}

    return result


def connected_user_ids() -> list[str]:
    users: set[str] = set()

    try:
        from src.calendar.service import get_all_connected_user_ids

        users.update(get_all_connected_user_ids())
    except Exception as exc:
        _log_sync_exception("Could not list connected calendar users: %s", exc)

    try:
        from src.slack_agent.router import get_all_connected_slack_user_ids

        users.update(get_all_connected_slack_user_ids())
    except Exception as exc:
        _log_sync_exception("Could not list connected Slack users: %s", exc)

    try:
        from src.github_agent.router import get_all_connected_github_user_ids

        users.update(get_all_connected_github_user_ids())
    except Exception as exc:
        _log_sync_exception("Could not list connected GitHub users: %s", exc)

    return sorted(users)


def fetch_latest_for_users(user_ids: Optional[Iterable[str]] = None) -> Dict:
    target_user_ids = list(user_ids) if user_ids is not None else connected_user_ids()
    results = [fetch_latest_for_user(user_id) for user_id in target_user_ids]

    try:
        from src.slack_agent.router import purge_old_slack_messages

        slack_purge = purge_old_slack_messages()
    except Exception as exc:
        _log_sync_exception("Slack purge failed after fetch: %s", exc)
        detail = _dependency_unavailable_detail("Slack purge") if _is_transient_dependency_error(exc) else str(exc)
        slack_purge = {"ok": False, "message": detail}

    return {
        "ok": all(
            item.get("calendar", {}).get("ok", False)
            and item.get("slack", {}).get("ok", False)
            and item.get("github", {}).get("ok", True)
            for item in results
        ),
        "scope": "selected_users" if user_ids is not None else "all_connected_users",
        "users": len(target_user_ids),
        "results": results,
        "retention": {
            "slack": slack_purge,
            "calendar": "Calendar sync keeps the current-month window and purges previous-month vectors.",
        },
    }
