"""
NUMA — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger("numa.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NUMA API starting up...")
    # Start background scheduler for Slack monitoring
    try:
        from app.monitor.scheduler import start_scheduler, run_monitoring_cycle
        start_scheduler(settings.CHECK_INTERVAL_MINUTES)
        run_monitoring_cycle()
    except Exception as exc:
        logger.warning(f"Scheduler start failed (non-fatal): {exc}")
    yield
    logger.info("NUMA API shutting down...")
    try:
        from app.monitor.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="NUMA API",
    version="2.0.0",
    description="Personal productivity backend with Slack integration",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:3000",  # CRA fallback
        "https://humblingly-khedival-declan.ngrok-free.dev",  # ngrok tunnel
        "https://your-production-domain.com",  # replace in prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registrations ────────────────────────────────────────────────────────
from app.routers import auth, dashboard, tasks, messages, schedule, analytics, chat

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(tasks.router)
app.include_router(messages.router)
app.include_router(schedule.router)
app.include_router(analytics.router)
app.include_router(chat.router)

# ── Slack Bolt ────────────────────────────────────────────────────────────────
from app.slack_bolt_handler import bolt_handler
from fastapi import Request as FastAPIRequest
from fastapi.responses import Response


@app.post("/slack/events")
async def slack_events(req: FastAPIRequest):
    if not bolt_handler:
        return JSONResponse(status_code=503, content={"error": "Slack not available"})
    return await bolt_handler.handle(req)


@app.post("/slack/commands")
async def slack_commands(req: FastAPIRequest):
    if not bolt_handler:
        return JSONResponse(status_code=503, content={"error": "Slack not available"})
    return await bolt_handler.handle(req)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/")
async def health():
    return {"status": "ok", "service": "NUMA API", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
