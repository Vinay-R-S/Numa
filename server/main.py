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

# Before the first router import, so the boot lines below and anything a module
# logs while importing already go through the redaction filter (NUMA-134 P6,
# PLAN 8). uvicorn has configured its own loggers by this point, which is why
# configure_logging() also hardens the ones that already exist.
from src.core.logging import configure_logging

configure_logging()

from src.auth.router import router as auth_router
from src.auth.dependencies import get_current_user, require_admin
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
from src.core.db import close_pool, init_db
from src.core.errors import register_exception_handlers
from src.core.scheduler import start_periodic_sync_scheduler, stop_periodic_sync_scheduler
from src.core.security import verify_encryption_key
from src.slack_agent.security import verify_signing_secret
from src.ai_settings.repository import ai_settings_repository

log = logging.getLogger(__name__)

# Origins never carry a trailing slash, so a FRONTEND_URL written with one would
# silently never match.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")

# The environment is declared, not inferred (NUMA-127 P6, PLAN 8). `IS_DEV = not
# FRONTEND_URL` conflated "which origin is allowed" with "which environment is
# this", and got both wrong: a deploy that forgot FRONTEND_URL silently opened
# the API to every origin on the internet, while a developer following
# .env.example - which sets FRONTEND_URL - never got the LAN regex the comment
# promised. Defaulting to production means a missing NUMA_ENV fails closed.
NUMA_ENV = os.environ.get("NUMA_ENV", "production").strip().lower()
IS_DEV = NUMA_ENV == "development"

# Loopback and the RFC1918 ranges only, so a phone on the same wifi still reaches
# the dev server while the old `https?://.*` no longer matches any site anywhere.
# Starlette fullmatches this, and the anchors keep it correct if that ever changes.
DEV_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost|127\.\d{1,3}\.\d{1,3}\.\d{1,3}|\[::1\]|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)

CORS_ORIGINS = [FRONTEND_URL] if FRONTEND_URL else []

if not IS_DEV and not CORS_ORIGINS:
    log.error(
        "FRONTEND_URL is unset and NUMA_ENV is not 'development'. Refusing every "
        "cross-origin browser request. Set FRONTEND_URL to the deployed origin, "
        "or NUMA_ENV=development for local work."
    )


def _check_encryption_key() -> None:
    """Fail the boot rather than a request (NUMA-128 P6, PLAN 8).

    A malformed key used to surface as a 500 from the settings page on the first
    save, and a missing one silently produced ciphertext nothing could read back.
    """
    verify_encryption_key(encrypted_rows_exist=ai_settings_repository.encrypted_key_count() > 0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: init_db(raise_on_error=True))
    await loop.run_in_executor(None, _check_encryption_key)
    verify_signing_secret()

    # In the executor, not on a throwaway daemon thread. `BackgroundScheduler`
    # starts its own thread and returns immediately, so the wrapper bought
    # nothing and cost us both the handle and the traceback.
    scheduler = await loop.run_in_executor(None, start_periodic_sync_scheduler)
    try:
        yield
    finally:
        # Order matters. A job still firing after the pool closed called
        # `_get_pool()`, found None, and opened a fresh pool against Postgres
        # after shutdown - the "too many clients" failure close_pool() exists to
        # prevent, once per reload (NUMA-142 P6, PLAN 7).
        await loop.run_in_executor(None, stop_periodic_sync_scheduler, scheduler)

        # The pool outlived the app: shutdown left its connections open for the
        # server to time out (NUMA-135 P6, PLAN 7).
        await loop.run_in_executor(None, close_pool)


app = FastAPI(title="Numa API", version="1.0.0", lifespan=lifespan)

# Services raise the typed errors from `core.errors`; routers catch them and
# re-raise as HTTPException, but a route that forgets leaks an AppError to
# Starlette, which answers a bare 500 and loses both the status the error
# carried and its message (NUMA-138 P6, PLAN 7). Registering the handler makes
# the `{detail}` envelope the outcome whether or not the router remembered.
register_exception_handlers(app)
AUDIO_ROOT = SERVER_ROOT / "audio"
AUDIO_ROOT.mkdir(parents=True, exist_ok=True)
IMAGE_ASSETS_ROOT = SERVER_ROOT / "assets" / "images"

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=DEV_ORIGIN_REGEX if IS_DEV else None,
    # Auth is a Bearer header read from localStorage, never a cookie, so the
    # browser has no credentials to send here. Keeping this off means an allowed
    # origin still cannot ride a logged-in session (NUMA-127).
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    # WWW-Authenticate is not CORS-safelisted, so a cross-origin client cannot
    # read it unless it is exposed. lib/http uses it to tell a dead session from
    # a domain 401 (NUMA-126); without this the check silently returns false the
    # day the client stops going through the Next proxy.
    expose_headers=["WWW-Authenticate"],
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
    """Unauthenticated liveness probe.

    It used to return the Qdrant host, the absolute embedding cache path and the
    embedder's raw failure string to anyone who asked. Infrastructure that polls
    this only needs the verdict; the diagnostics moved behind the admin gate
    (NUMA-142 P6, PLAN 8).
    """
    from src.memory.service import memory_service

    return {
        "status": "ok",
        "vector_memory": {"enabled": memory_service.enabled},
    }


@app.get("/health/details", include_in_schema=False)
def health_details(_: dict = Depends(require_admin)):
    """Full diagnostics: admin-only, since it names hosts, paths and failures."""
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
