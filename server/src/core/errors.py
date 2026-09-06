"""Application error hierarchy and FastAPI handlers (NUMA-102).

Registered on the app in `main.py` (NUMA-138 P6, PLAN 7), so any AppError that
reaches the ASGI layer becomes its own status and `{detail}` rather than a bare
500. Routers that already catch AppError and re-raise HTTPException keep working
unchanged; this is the floor under the ones that do not (PLAN 5.1, 7).
"""
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    detail = "Internal server error"

    #: Whether `detail` is safe to return to the caller on a 5xx. False by
    #: default because live code builds these by interpolation
    #: (`AppError(f"DB error: {exc}")`), which is exactly what must not be
    #: echoed. A raiser that wrote the string for the user opts in with
    #: `public=True` (NUMA-142 P6 review).
    public_detail = False

    def __init__(
        self,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        public: bool = False,
    ):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if public:
            self.public_detail = True
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


class PublicHTTPException(StarletteHTTPException):
    """An HTTPException whose detail was written for the caller.

    The 5xx redaction below cannot tell a message an author wrote for the user
    ("GitHub took too long to respond") from one built by interpolating a driver
    exception, so it flattens both. A router that is forwarding a detail it
    knows is safe raises this instead and keeps its wording
    (NUMA-142 P6 review).
    """


def http_error_from(exc: AppError) -> StarletteHTTPException:
    """Re-raise an AppError as the HTTPException a router returns.

    Preserves the safe-detail decision the raiser made, which a plain
    `HTTPException(exc.status_code, exc.detail)` threw away.
    """
    detail = exc.detail
    public = exc.public_detail or exc.status_code < 500
    if not public and exc.status_code >= 500:
        detail = type(exc).detail

    factory = PublicHTTPException if public else StarletteHTTPException
    return factory(status_code=exc.status_code, detail=detail)


# The generic 5xx body. Anything more specific risks being the interpolated
# driver text this exists to keep out of responses.
_SERVER_ERROR_DETAIL = "Internal server error"


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
            # The detail goes to the log, never to the caller. Live code builds
            # these by interpolation - `AppError(f"DB error: {exc}")` - so
            # echoing it handed schema names, column names and connection
            # details to any authenticated client (NUMA-142 P6, PLAN 8). A 4xx
            # detail is written for the caller and is safe to return.
            # type(exc).detail, not AppError.detail: a subclass carries its own
            # safe wording, and reading the base attribute turned every
            # UpstreamError 502 into "Internal server error". An instance that
            # opted in with `public=True` keeps the message it was given.
            detail = exc.detail if exc.public_detail else type(exc).detail
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": detail},
            )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException):
        """Redact 5xx detail on the path the feature routers actually take.

        Handling AppError alone covered only errors that escape to the ASGI
        layer. Every feature router catches AppError and re-raises it as an
        HTTPException carrying the same detail, and `calendar/router.py` builds
        `f"{action}: {exc}"` outright, so `AppError(f"DB error: {exc}")` still
        reached clients on the normal path.

        4xx is passed through untouched, headers included: `lib/http` reads
        `WWW-Authenticate` to tell a dead session from a domain 401 (NUMA-126),
        and losing it here would break that silently. So is a
        `PublicHTTPException`, whose detail the raiser wrote for the caller:
        flattening those turned "GitHub took too long to respond" and "Could not
        generate the summary right now" into "Internal server error"
        (NUMA-142 P6 review). A 5xx is still logged either way.
        """
        if exc.status_code >= 500:
            log.exception(
                "%s %s failed: %s", request.method, request.url.path, exc.detail,
            )
            if not isinstance(exc, PublicHTTPException):
                exc = StarletteHTTPException(
                    status_code=exc.status_code,
                    detail=_SERVER_ERROR_DETAIL,
                    headers=getattr(exc, "headers", None),
                )
        return await default_http_exception_handler(request, exc)
