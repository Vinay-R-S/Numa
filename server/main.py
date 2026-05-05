import logging
import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

SERVER_ROOT = Path(__file__).resolve().parent
load_dotenv(SERVER_ROOT / ".env")

from src.auth.router import router as auth_router
from src.auth.dependencies import get_current_user
from src.tasks.router import router as tasks_router
from src.calendar.router import router as calendar_router
from src.calendar_agent.router import router as calendar_agent_router
from src.master_agent.router import router as master_agent_router
from src.slack_agent.router import router as slack_router
from src.health_agent.router import router as health_agent_router
from src.ai_settings.router import router as ai_settings_router
from src.journal.router import router as journal_router
from src.github_agent.router import router as github_router
from src.leetcode.router import router as leetcode_router
from src.dashboard.router import router as dashboard_router
from src.db import init_db

log = logging.getLogger(__name__)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "")

# In production set FRONTEND_URL to your exact origin.
# During local dev we match any HTTP/HTTPS origin via regex so any device on
# the network can connect. allow_origin_regex echoes the real origin back
# (unlike "*") which lets allow_credentials work correctly.
IS_DEV = not FRONTEND_URL

app = FastAPI(title="Numa API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if not IS_DEV else [],
    allow_origin_regex=r"https?://.*" if IS_DEV else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Background scheduler ──────────────────────────────────────────────────────

def _start_periodic_sync_scheduler():
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
            from src.data_sync import fetch_latest_for_users

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


@app.on_event("startup")
async def on_startup():
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, init_db)

    import threading
    threading.Thread(target=_start_periodic_sync_scheduler, daemon=True).start()

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(calendar_router)
app.include_router(calendar_agent_router)
app.include_router(master_agent_router)
app.include_router(slack_router)
app.include_router(health_agent_router)
app.include_router(ai_settings_router)
app.include_router(journal_router)
app.include_router(github_router)
app.include_router(leetcode_router)
app.include_router(dashboard_router)


# ── Public ────────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "Welcome to the Numa API"}


@app.get("/health")
def health_check():
    """Basic health + Qdrant/memory status check."""
    from src.memory.service import memory_service

    mem_status: dict = {
        "enabled": memory_service.enabled,
        "mode": memory_service.qdrant_mode,
        "embedding_provider": memory_service.embedding_provider,
        "embedding_model": memory_service.local_embedding_model,
        "embedding_cache": memory_service._embedding_cache_dir(),
        "collections": {
            "memory": "{user_id}_memory",
            "calendar": "{user_id}_calendar",
            "slack": "{user_id}_slack",
        },
        "host": memory_service.qdrant_host,
        "api_key_configured": bool(memory_service.qdrant_api_key),
    }

    return {
        "status": "ok",
        "vector_memory": mem_status,
    }


# ── Protected ─────────────────────────────────────────────────────────────────
@app.get("/home")
def home(current_user: dict = Depends(get_current_user)):
    """Protected home endpoint - requires a valid JWT."""
    return {
        "message": f"Welcome, {current_user.get('full_name') or current_user['email']}!",
        "user_id": current_user["sub"],
        "email": current_user["email"],
    }
