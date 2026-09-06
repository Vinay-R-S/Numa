"""Background scheduler for periodic sync and retention jobs (NUMA-102)."""
import logging
import os
import threading
from typing import Any, Optional

log = logging.getLogger(__name__)

# How long shutdown waits for a job that is still running. Bounded on purpose:
# the periodic fetch syncs every connected user over HTTP and can run for
# minutes, and an unbounded wait outlasts the process manager's grace period,
# which ends in SIGKILL and skips the `close_pool()` this ordering exists to
# guarantee. Overrunning the wait is logged and shutdown proceeds.
_SHUTDOWN_WAIT_SECONDS = 10.0


def start_periodic_sync_scheduler() -> Optional[Any]:
    """
    Start an APScheduler background job that fetches latest external app data
    for every connected user every 30 minutes by default.

    This acts as a safety net for missed webhook events and runs retention cleanup.

    Returns the scheduler so the caller can stop it. It used to return nothing
    and be launched on a bare daemon thread, which meant two things: the app had
    no handle to shut it down, so jobs kept firing after `close_pool()` and
    rebuilt the pool it had just closed (NUMA-142 P6, PLAN 7); and any failure
    past the ImportError guard - a non-numeric interval, a bad timezone - killed
    that thread silently, so background sync and the daily purge never ran while
    the app booted green and /health reported ok.

    Every failure here returns None rather than raising. Without the daemon
    thread that used to swallow them, this runs inline in the app's lifespan, so
    an unguarded raise would refuse the boot over a disabled background job.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
        from apscheduler.triggers.cron import CronTrigger  # type: ignore
        from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
    except ImportError:
        log.warning(
            "APScheduler not installed - periodic app fetch disabled. "
            "Install apscheduler to enable background sync."
        )
        return None

    raw_interval = os.getenv("SYNC_SCHEDULER_INTERVAL_MINUTES", "30")
    try:
        interval_minutes = max(1, int(raw_interval))
    except ValueError:
        log.warning(
            "SYNC_SCHEDULER_INTERVAL_MINUTES=%r is not a number; using 30 minutes",
            raw_interval,
        )
        interval_minutes = 30

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
            from src.health_agent.persistence import purge_old_health_snapshots
            deleted = purge_old_health_snapshots()
            log.info("Daily health purge complete: %d rows deleted", deleted)
        except Exception as exc:
            log.warning("Daily health purge failed: %s", exc)

    # One guard over construction, registration and start. An invalid timezone
    # or a trigger the installed APScheduler rejects is a disabled feature, not
    # a reason to take the app down.
    try:
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
    except Exception:
        log.error(
            "Background scheduler unavailable; periodic sync and the daily purge are disabled",
            exc_info=True,
        )
        return None

    log.info("Periodic app fetch scheduled every %d minute(s).", interval_minutes)
    log.info("Daily health purge scheduled at 8:00 AM IST.")
    return scheduler


def stop_periodic_sync_scheduler(scheduler: Optional[Any]) -> None:
    """Stop the scheduler, waiting a bounded time for a job still running.

    Waiting at all matters: a sync job mid-write holds a pooled connection, and
    returning before it finishes is what let `close_pool()` run underneath it.
    Waiting forever matters too, in the other direction - see
    `_SHUTDOWN_WAIT_SECONDS`. APScheduler's `shutdown` takes no timeout, so the
    bound is applied by joining it on a thread.
    """
    if scheduler is None:
        return

    def _shutdown() -> None:
        try:
            scheduler.shutdown(wait=True)
        except Exception:
            log.warning("Background scheduler did not shut down cleanly", exc_info=True)

    worker = threading.Thread(target=_shutdown, name="scheduler-shutdown", daemon=True)
    worker.start()
    worker.join(timeout=_SHUTDOWN_WAIT_SECONDS)

    if worker.is_alive():
        log.warning(
            "Background scheduler still running a job after %.0fs; continuing shutdown",
            _SHUTDOWN_WAIT_SECONDS,
        )
        return

    log.info("Background scheduler stopped.")
