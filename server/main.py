import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from src.audio_library.router import router as audio_library_router
from src.core.db import init_db
from src.core.scheduler import start_periodic_sync_scheduler

log = logging.getLogger(__name__)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "")

# In production set FRONTEND_URL to your exact origin.
# During local dev we match any HTTP/HTTPS origin via regex so any device on
# the network can connect. allow_origin_regex echoes the real origin back
# (unlike "*") which lets allow_credentials work correctly.
IS_DEV = not FRONTEND_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: init_db(raise_on_error=True))

    import threading
    threading.Thread(target=start_periodic_sync_scheduler, daemon=True).start()
    yield


app = FastAPI(title="Numa API", version="1.0.0", lifespan=lifespan)
AUDIO_ROOT = SERVER_ROOT / "audio"
AUDIO_ROOT.mkdir(parents=True, exist_ok=True)
IMAGE_ASSETS_ROOT = SERVER_ROOT / "assets" / "images"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if not IS_DEV else [],
    allow_origin_regex=r"https?://.*" if IS_DEV else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(audio_library_router)

# Compatibility aliases (NUMA-117). The client proxy at client/src/app/api/
# [...path]/route.ts forwards /api/<x> to BACKEND/<x>, dropping exactly one
# segment, so a router that also carries /api in its own prefix is unreachable
# through the proxy. Those five routers now mount without it, like the other
# eight, and are re-mounted here under /api so every caller that hits FastAPI
# directly (the registered GitHub OAuth redirect URI, lib/aiSettings.ts,
# settings/page.tsx) keeps its URL. Hidden from the schema so each path appears
# once in the OpenAPI document.
for _aliased_router in (
    ai_settings_router,
    journal_router,
    github_router,
    leetcode_router,
    dashboard_router,
):
    app.include_router(_aliased_router, prefix="/api", include_in_schema=False)

app.mount("/audio", StaticFiles(directory=str(AUDIO_ROOT)), name="audio")
app.mount("/assets/images", StaticFiles(directory=str(IMAGE_ASSETS_ROOT)), name="image_assets")


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
        "rate_limiter": _rate_limiter_status(),
        "embedding_cache": _embedding_cache_status(),
    }


def _rate_limiter_status() -> dict:
    try:
        from src.core.rate_limiter import rate_limiter
        return rate_limiter.get_status()
    except Exception:
        return {"enabled": False}


def _embedding_cache_status() -> dict:
    try:
        from src.core.embedder import embedder
        return embedder.cache_stats
    except Exception:
        return {}


# ── Protected ─────────────────────────────────────────────────────────────────
@app.get("/home")
def home(current_user: dict = Depends(get_current_user)):
    """Protected home endpoint - requires a valid JWT."""
    return {
        "message": f"Welcome, {current_user.get('full_name') or current_user['email']}!",
        "user_id": current_user["sub"],
        "email": current_user["email"],
    }
