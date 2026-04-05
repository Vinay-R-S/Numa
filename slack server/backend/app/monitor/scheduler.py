"""
Background scheduler — runs a Slack monitoring cycle every N minutes.
Designed to be started from FastAPI's lifespan context.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.monitor.slack_fetcher import fetch_new_messages
from app.monitor.analyzer import analyze_messages
from app.monitor.notifier.notification_service import dispatch_notifications

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_monitoring_cycle() -> None:
    """
    Single monitoring cycle:
      1. Fetch new messages from every configured channel.
      2. Analyse and categorise them.
      3. Dispatch notifications if anything noteworthy was found.
    """
    logger.info("Monitor cycle starting…")

    raw_channels = settings.MONITOR_CHANNELS
    if not raw_channels:
        logger.warning("MONITOR_CHANNELS is empty — nothing to monitor.")
        return

    channels = [c.strip() for c in raw_channels.split(",") if c.strip()]

    all_messages: list = []
    for channel_id in channels:
        try:
            msgs = fetch_new_messages(channel_id)
            all_messages.extend(msgs)
        except Exception as exc:
            logger.error("Error fetching channel %s: %s", channel_id, exc)

    if not all_messages:
        logger.info("No new messages found across %d channel(s).", len(channels))
        return

    summary = analyze_messages(all_messages, user_id=settings.NOTIFICATION_USER_ID)
    dispatch_notifications(summary)
    logger.info("Monitor cycle complete. Processed %d message(s).", len(all_messages))


def start_scheduler(interval_minutes: int | None = None) -> None:
    """Start the background scheduler. Safe to call multiple times (idempotent)."""
    if scheduler.running:
        return

    effective_interval = interval_minutes or settings.CHECK_INTERVAL_MINUTES

    scheduler.add_job(
        run_monitoring_cycle,
        trigger=IntervalTrigger(minutes=effective_interval),
        id="slack_monitor",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Slack monitor started — polling every %d minute(s).", effective_interval)

    try:
        run_monitoring_cycle()
    except Exception as exc:
        logger.warning("Initial monitoring cycle failed (non-fatal): %s", exc)


def stop_scheduler() -> None:
    """Gracefully stop the scheduler on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Slack monitor stopped.")
