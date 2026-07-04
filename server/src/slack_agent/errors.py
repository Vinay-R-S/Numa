"""Transient-dependency error helpers for Slack (NUMA-105 P3, PLAN 16.2).

Leaf module. Distinguishes transient network/DB blips (logged at debug, surfaced
as "temporarily unavailable") from real errors. Extracted verbatim from
slack_agent/router.py; router.py re-exports these names.
"""
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


def _temporary_unavailable_detail(service: str) -> str:
    return f"{service} temporarily unavailable; sync skipped"


def _log_dependency_exception(message: str, exc: Exception, *args) -> None:
    if _is_transient_dependency_error(exc):
        log.debug(message, *args, exc)
    else:
        log.warning(message, *args, exc)
