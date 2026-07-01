"""Background scheduler for periodic sync and retention jobs (NUMA-102)."""
import logging
import os

log = logging.getLogger(__name__)


def start_periodic_sync_scheduler():
    """
    Start an APScheduler background job that fetches latest external app data
    for every connected user every 30 minutes by default.

    This acts as a safety net for missed webhook events and runs retention cleanup.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
        from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
    except ImportError:
        log.warning(
            "APScheduler not installed - periodic app fetch disabled. "
            "Install apscheduler to enable background sync."
        )
        return

    interval_minutes = max(1, int(os.getenv("SYNC_SCHEDULER_INTERVAL_MINUTES", "30")))

    def _periodic_fetch_job():
        try:
            from src.core.data_sync import fetch_latest_for_users

            result = fetch_latest_for_users()
            log.info(
                "Periodic app fetch complete for %d connected user(s): ok=%s",
                result.get("users", 0),
                result.get("ok"),
            )
        except Exception as exc:
            log.warning("Periodic app fetch failed: %s", exc)

    def _daily_health_purge_job():
        """Delete health snapshots older than 8 days. Runs at 8 AM IST."""
        try:
            from src.health_agent.router import purge_old_health_snapshots
            deleted = purge_old_health_snapshots()
            log.info("Daily health purge complete: %d rows deleted", deleted)
        except Exception as exc:
            log.warning("Daily health purge failed: %s", exc)

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        _periodic_fetch_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="periodic_app_fetch",
        replace_existing=True,
        misfire_grace_time=300,
        max_instances=1,
        coalesce=True,
    )

    from apscheduler.triggers.cron import CronTrigger  # type: ignore
    scheduler.add_job(
        _daily_health_purge_job,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_health_purge",
        replace_existing=True,
        misfire_grace_time=600,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    log.info("Periodic app fetch scheduled every %d minute(s).", interval_minutes)
    log.info("Daily health purge scheduled at 8:00 AM IST.")
