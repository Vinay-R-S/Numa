"""
Notification service — dispatches email + Slack DM summaries and stores a nudge in Supabase.
"""
import logging
from typing import Dict, List, Any

from app.config import settings
from app.database import get_supabase
from app.monitor.notifier.email_notifier import send_email
from app.monitor.notifier.slack_notifier import send_slack_dm

logger = logging.getLogger(__name__)


def _format_text(summary: Dict[str, List[Dict[str, Any]]]) -> str:
    lines = ["Slack Activity Summary (NUMA)\n"]

    def _section(title: str, items: List[Dict]) -> None:
        if not items:
            return
        lines.append(f"\n{title}:")
        for msg in items:
            text = msg.get("text", "").replace("\n", " ").strip()
            if len(text) > 120:
                text = text[:117] + "..."
            lines.append(f"  • {text}")

    _section("Mentions", summary.get("mentions", []))
    _section("Meetings", summary.get("meetings", []))
    _section("Urgent",   summary.get("urgent", []))

    general = summary.get("general", [])
    if general:
        if len(general) <= 5:
            _section("General", general)
        else:
            lines.append(f"\nGeneral: {len(general)} updates")

    return "\n".join(lines)


def _store_nudge(summary: Dict[str, List[Dict[str, Any]]]) -> None:
    """Persist an aggregate nudge to Supabase so the dashboard can surface it."""
    total = sum(len(v) for v in summary.values())
    if total == 0:
        return

    parts: List[str] = []
    if summary.get("mentions"):
        parts.append(f"{len(summary['mentions'])} mention(s)")
    if summary.get("urgent"):
        parts.append(f"{len(summary['urgent'])} urgent message(s)")
    if summary.get("meetings"):
        parts.append(f"{len(summary['meetings'])} meeting-related message(s)")

    message = "Activity: " + ", ".join(parts) if parts else f"{total} new Slack message(s)"

    try:
        # Insert a global nudge (user_id NULL = system-wide)
        get_supabase().table("nudges").insert({
            "user_id":  None,
            "type":     "slack_summary",
            "message":  message,
            "metadata": {"counts": {k: len(v) for k, v in summary.items()}},
            "is_read":  False,
        }).execute()
    except Exception as exc:
        logger.warning("Could not store nudge in Supabase: %s", exc)


def dispatch_notifications(summary: Dict[str, List[Dict[str, Any]]]) -> None:
    """Main entry-point called by the scheduler after every monitoring cycle."""
    total = sum(len(v) for v in summary.values())
    if total == 0:
        logger.info("Nothing to report — skipping notifications.")
        return

    logger.info("Dispatching notifications for %d messages.", total)

    email_ok = False
    slack_ok = False

    if settings.EMAIL_ENABLED:
        email_ok = send_email(_format_text(summary))

    slack_ok = send_slack_dm(summary_data=summary)

    _store_nudge(summary)

    if not email_ok and not slack_ok:
        logger.warning("Both notification channels failed.")
