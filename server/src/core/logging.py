"""Logging configuration with secret redaction (NUMA-102).

Additive: not yet wired into startup. Call configure_logging() from lifespan when
adopting. Redacts tokens, keys, and JWTs from log output (PLAN 8).
"""
import logging
import re

_REDACT_PATTERNS = [
    re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),        # Slack tokens
    re.compile(r"gh[pousr]_[A-Za-z0-9]+"),          # GitHub tokens
    re.compile(r"sk-[A-Za-z0-9-]{16,}"),            # OpenAI-style keys
    re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.I),  # bearer tokens
    re.compile(r"eyJ[A-Za-z0-9._-]{10,}"),          # JWTs
]
_MASK = "[REDACTED]"


def _redact(text: str) -> str:
    for pat in _REDACT_PATTERNS:
        text = pat.sub(_MASK, text)
    return text


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                _redact(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler.addFilter(RedactionFilter())
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
