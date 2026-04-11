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

def _start_nightly_sync_scheduler():
    """
    Start an APScheduler background job that runs a full Google Calendar sync
    for every connected user at the configured time (default: 02:00 IST).

    This acts as a safety net for missed webhook events and also triggers the
    monthly purge automatically on the 1st of each new month.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
        from apscheduler.triggers.cron import CronTrigger  # type: ignore
    except ImportError:
        log.warning(
            "APScheduler not installed — nightly calendar sync disabled. "
            "Install apscheduler to enable background sync."
        )
        return

    from src.calendar.service import get_events_for_frontend, get_all_connected_user_ids

    scheduler_hour   = int(os.getenv("SYNC_SCHEDULER_HOUR",   "2"))
    scheduler_minute = int(os.getenv("SYNC_SCHEDULER_MINUTE", "0"))

    def _nightly_job():
        user_ids = get_all_connected_user_ids()
        log.info("Nightly calendar sync: found %d connected user(s).", len(user_ids))
        for uid in user_ids:
            try:
                get_events_for_frontend(user_id=uid, force_refresh=True)
                log.info("Nightly sync complete for user %s", uid)
            except Exception as exc:
                log.warning("Nightly sync failed for user %s: %s", uid, exc)

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        _nightly_job,
        trigger=CronTrigger(hour=scheduler_hour, minute=scheduler_minute),
        id="nightly_calendar_sync",
        replace_existing=True,
        misfire_grace_time=300,  # allow up to 5 min late start
    )
    scheduler.start()
    log.info(
        "Nightly calendar sync scheduled at %02d:%02d IST.",
        scheduler_hour,
        scheduler_minute,
    )


@app.on_event("startup")
def on_startup():
    init_db()
    _start_nightly_sync_scheduler()

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(calendar_router)
app.include_router(calendar_agent_router)
app.include_router(master_agent_router)


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
        "mode": "local_file" if memory_service._using_local_mode else ("remote" if memory_service.qdrant_url else "disabled"),
        "embedding_provider": memory_service.embedding_provider,
        "collection": memory_service.collection_name,
    }

    if memory_service._using_local_mode:
        mem_status["local_path"] = memory_service.qdrant_local_path

    return {
        "status": "ok",
        "vector_memory": mem_status,
    }


# ── Protected ─────────────────────────────────────────────────────────────────
@app.get("/home")
def home(current_user: dict = Depends(get_current_user)):
    """Protected home endpoint — requires a valid JWT."""
    return {
        "message": f"Welcome, {current_user.get('full_name') or current_user['email']}!",
        "user_id": current_user["sub"],
        "email": current_user["email"],
    }
