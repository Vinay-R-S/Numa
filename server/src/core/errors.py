"""Application error hierarchy and FastAPI handlers (NUMA-102).

Additive: not yet registered on the app. Call register_exception_handlers(app)
to emit the {detail} envelope once features adopt these errors (PLAN 5.1, 7).
"""
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


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
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
