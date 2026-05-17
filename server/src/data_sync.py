import logging
from typing import Dict, Iterable, Optional

log = logging.getLogger(__name__)


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
        log.warning("Calendar fetch failed for user %s: %s", user_id, exc)
        result["calendar"] = {"ok": False, "fetched": 0, "detail": str(exc)}

    try:
        from src.slack_agent.router import fetch_latest_slack_for_user

        result["slack"] = fetch_latest_slack_for_user(user_id)
    except Exception as exc:
        log.warning("Slack fetch failed for user %s: %s", user_id, exc)
        result["slack"] = {"ok": False, "fetched": 0, "channels": 0, "detail": str(exc)}

    try:
        from src.health_agent.router import sync_health_for_user

        result["health"] = sync_health_for_user(user_id)
    except Exception as exc:
        log.warning("Health sync failed for user %s: %s", user_id, exc)
        result["health"] = {"ok": False, "detail": str(exc)}

    try:
        from src.github_agent.router import fetch_and_store_github_stats_for_user

        result["github"] = fetch_and_store_github_stats_for_user(user_id)
    except Exception as exc:
        log.warning("GitHub sync failed for user %s: %s", user_id, exc)
        result["github"] = {"ok": False, "detail": str(exc)}

    return result


def connected_user_ids() -> list[str]:
    users: set[str] = set()

    try:
        from src.calendar.service import get_all_connected_user_ids

        users.update(get_all_connected_user_ids())
    except Exception as exc:
        log.warning("Could not list connected calendar users: %s", exc)

    try:
        from src.slack_agent.router import get_all_connected_slack_user_ids

        users.update(get_all_connected_slack_user_ids())
    except Exception as exc:
        log.warning("Could not list connected Slack users: %s", exc)

    try:
        from src.github_agent.router import get_all_connected_github_user_ids

        users.update(get_all_connected_github_user_ids())
    except Exception as exc:
        log.warning("Could not list connected GitHub users: %s", exc)

    return sorted(users)


def fetch_latest_for_users(user_ids: Optional[Iterable[str]] = None) -> Dict:
    target_user_ids = list(user_ids) if user_ids is not None else connected_user_ids()
    results = [fetch_latest_for_user(user_id) for user_id in target_user_ids]

    try:
        from src.slack_agent.router import purge_old_slack_messages

        slack_purge = purge_old_slack_messages()
    except Exception as exc:
        log.warning("Slack purge failed after fetch: %s", exc)
        slack_purge = {"ok": False, "message": str(exc)}

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
