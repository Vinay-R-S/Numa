"""GitHub helpers (NUMA-109 P3, PLAN 16.7): transient-error classification and
cached-stats shaping. Pure functions, no I/O.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_TRANSIENT_DEPENDENCY_MARKERS = (
    "getaddrinfo failed",
    "could not translate host name",
    "name or service not known",
    "temporary failure in name resolution",
    "unable to find the server",
    "server closed the connection unexpectedly",
    "connection unexpectedly",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
)


def _is_transient_dependency_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_DEPENDENCY_MARKERS)


def _log_dependency_exception(message: str, exc: Exception, *args) -> None:
    if _is_transient_dependency_error(exc):
        log.debug(message, *args, exc)
    else:
        log.warning(message, *args, exc)


def _strip_internal_stats_fields(stats: dict) -> dict:
    cleaned = dict(stats)
    cleaned.pop("_last_synced_at", None)
    cleaned.pop("_profile_synced_at", None)
    return cleaned
