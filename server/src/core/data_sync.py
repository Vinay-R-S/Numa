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

_NOT_CONNECTED_ERROR_MARKERS = (
    "is not connected",
    "not connected",
    "start oauth",
    "please reconnect",
    "reconnect google",
    "session expired",
    "missing newly required scopes",
    "insufficient authentication scopes",
    "access_token_scope_insufficient",
)


def _is_transient_dependency_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_ERROR_MARKERS)


def _is_not_connected_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _NOT_CONNECTED_ERROR_MARKERS)


def _dependency_unavailable_detail(service: str) -> str:
    return f"{service} temporarily unavailable; sync skipped"


def _log_sync_exception(message: str, exc: Exception, *args) -> None:
    if _is_transient_dependency_error(exc) or _is_not_connected_error(exc):
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
        from src.calendar.service import get_events_for_frontend, has_calendar_credentials

        if has_calendar_credentials(user_id):
            events = get_events_for_frontend(user_id=user_id, force_refresh=True)
            result["calendar"] = {
                "ok": True,
                "fetched": len(events),
                "detail": "Calendar fetch complete",
            }
    except Exception as exc:
        _log_sync_exception("Calendar fetch failed for user %s: %s", exc, user_id)
        if _is_not_connected_error(exc):
            result["calendar"] = {"ok": True, "fetched": 0, "detail": "not connected"}
        else:
            detail = _dependency_unavailable_detail("Calendar") if _is_transient_dependency_error(exc) else str(exc)
            result["calendar"] = {"ok": False, "fetched": 0, "detail": detail}

    try:
        from src.slack_agent.events import fetch_latest_slack_for_user

        result["slack"] = fetch_latest_slack_for_user(user_id)
    except Exception as exc:
        _log_sync_exception("Slack fetch failed for user %s: %s", exc, user_id)
        detail = _dependency_unavailable_detail("Slack") if _is_transient_dependency_error(exc) else str(exc)
        result["slack"] = {"ok": False, "fetched": 0, "channels": 0, "detail": detail}

    try:
        from src.calendar.service import has_calendar_credentials
        from src.health_agent.sync import sync_health_for_user

        if has_calendar_credentials(user_id):
            health_result = sync_health_for_user(user_id)
            if health_result.get("not_connected"):
                health_result["ok"] = True
            result["health"] = health_result
        else:
            result["health"] = {"ok": True, "detail": "Google Fit not connected"}
    except Exception as exc:
        _log_sync_exception("Health sync failed for user %s: %s", exc, user_id)
        if _is_not_connected_error(exc):
            result["health"] = {"ok": True, "detail": "not connected"}
        else:
            detail = _dependency_unavailable_detail("Health") if _is_transient_dependency_error(exc) else str(exc)
            result["health"] = {"ok": False, "detail": detail}

    try:
        from src.github_agent.sync import fetch_and_store_github_stats_for_user

        github_result = fetch_and_store_github_stats_for_user(user_id)
        # "Not connected" is not a sync failure, exactly as the calendar, Slack
        # and health branches already treat it. Left as ok=False, every user
        # without a linked GitHub made the aggregate permanently False, so the
        # scheduler's `ok=%s` log line was never a usable alarm
        # (NUMA-142 P6 review).
        if not github_result.get("ok") and _is_not_connected_error(
            Exception(str(github_result.get("detail") or ""))
        ):
            github_result = {"ok": True, "detail": github_result.get("detail")}
        result["github"] = github_result
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
        from src.slack_agent.persistence import get_all_connected_slack_user_ids

        users.update(get_all_connected_slack_user_ids())
    except Exception as exc:
        _log_sync_exception("Could not list connected Slack users: %s", exc)

    try:
        from src.github_agent.persistence import get_all_connected_github_user_ids

        users.update(get_all_connected_github_user_ids())
    except Exception as exc:
        _log_sync_exception("Could not list connected GitHub users: %s", exc)

    return sorted(users)


def fetch_latest_for_users(user_ids: Optional[Iterable[str]] = None) -> Dict:
    target_user_ids = list(user_ids) if user_ids is not None else connected_user_ids()
    results = [fetch_latest_for_user(user_id) for user_id in target_user_ids]

    try:
        from src.slack_agent.service import slack_service

        slack_purge = slack_service.purge_old_messages()
    except Exception as exc:
        _log_sync_exception("Slack purge failed after fetch: %s", exc)
        detail = _dependency_unavailable_detail("Slack purge") if _is_transient_dependency_error(exc) else str(exc)
        slack_purge = {"ok": False, "message": detail}

    return {
        # All four domains, one default. Health was missing entirely, so a
        # failed health sync reported the whole run ok, and github defaulted to
        # True where its siblings defaulted to False (NUMA-142 P6, PLAN 7).
        "ok": all(
            all(
                item.get(domain, {}).get("ok", False)
                for domain in ("calendar", "slack", "health", "github")
            )
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
