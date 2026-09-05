"""Application error hierarchy and FastAPI handlers (NUMA-102).

Registered on the app in `main.py` (NUMA-138 P6, PLAN 7), so any AppError that
reaches the ASGI layer becomes its own status and `{detail}` rather than a bare
500. Routers that already catch AppError and re-raise HTTPException keep working
unchanged; this is the floor under the ones that do not (PLAN 5.1, 7).
"""
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: Optional[str] = None, status_code: Optional[int] = None):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFound(AppError):
    status_code = 404
    detail = "Not found"


class Forbidden(AppError):
    status_code = 403
    detail = "Forbidden"


class Conflict(AppError):
    status_code = 409
    detail = "Conflict"


class ValidationError(AppError):
    status_code = 422
    detail = "Validation error"


class UpstreamError(AppError):
    status_code = 502
    detail = "Upstream service error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # A 4xx is the caller's problem and says so in the response; a 5xx is
        # ours, and before this handler existed uvicorn logged its traceback.
        # Answering tidily without logging would have bought the envelope by
        # losing the cause - `AppError(f"DB error: {exc}") from exc` would reach
        # the client and leave nothing in the log at all.
        if exc.status_code >= 500:
            log.exception("%s %s failed: %s", request.method, request.url.path, exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
