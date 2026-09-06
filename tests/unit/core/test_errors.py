"""Regression tests for `core/errors` (NUMA-142 P6).

Error envelope. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


def test_interpolated_5xx_detail_is_not_returned_to_the_caller():
    """`AppError(f"DB error: {exc}")` reached authenticated clients."""
    from src.core.errors import AppError, http_error_from

    leaky = AppError('DB error: relation "public.tasks" does not exist')
    assert "tasks" not in http_error_from(leaky).detail
    assert http_error_from(leaky).detail == "Internal server error"


def test_author_written_5xx_detail_survives_redaction():
    """The blanket redaction flattened messages written for the user."""
    from src.core.errors import AppError, PublicHTTPException, http_error_from

    friendly = AppError("GitHub took too long to respond.", 504, public=True)
    mapped = http_error_from(friendly)

    assert isinstance(mapped, PublicHTTPException)
    assert mapped.detail == "GitHub took too long to respond."


def test_subclass_default_detail_is_kept():
    """Reading AppError.detail turned every UpstreamError 502 into a 500 body."""
    from src.core.errors import UpstreamError, http_error_from

    assert http_error_from(UpstreamError()).detail == "Upstream service error"


def test_4xx_detail_is_passed_through():
    from src.core.errors import AppError, http_error_from

    assert http_error_from(AppError("Slack not connected", 400)).detail == "Slack not connected"
