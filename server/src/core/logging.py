"""Logging configuration with secret redaction (NUMA-102, wired on NUMA-134 P6).

PLAN 8 says never log tokens, API keys, JWTs or PII. The redaction filter this
module has carried since NUMA-102 was never wired into a startup path, so
nothing in the running app was redacted; `main.py` and `scripts/init_db.py` call
`configure_logging()` now, and it is the only place that configures logging.

Redaction happens twice on purpose, because one hook alone cannot cover
everything a record can carry:

- `RedactionFilter` rewrites the record at log time, so it is already clean
  wherever it goes, including handlers this module did not install (uvicorn's
  access handler being the one that matters: the calendar SSE stream carries its
  scoped token in the query string, and uvicorn logs the full path).
- `RedactingFormatter` redacts the finished string, which is the only hook that
  sees a traceback. `log.exception(...)` on an HTTP error whose URL carries a
  key would otherwise print it in full, and the filter cannot reach it.

Two rules the patterns follow, both learned from getting them wrong first:

- Every quantifier is bounded. `re` backtracks, and an unbounded run inside a
  pattern that can fail late is quadratic in the length of the line: a 40KB log
  line took ten seconds to redact, synchronously, on the event loop.
- A secret key is matched after an underscore, not on a word boundary. `_` is a
  word character, so `\\b` never fires inside `SLACK_CLIENT_SECRET` - and every
  secret this app reads is an env var with a prefix.
"""
import logging
import os
import re

_MASK = "[REDACTED]"

# Keys whose value is a credential wherever it appears as `key=value`,
# `key: value` or `"key": "value"` (query strings, JSON bodies, repr of a dict).
# Longest alternatives first: `re` alternation is leftmost-first, so a bare
# `secret` listed before `secret_key` would leave `_KEY=` in the clear.
_SECRET_KEY = (
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"bot[_-]?token|user[_-]?token|stream[_-]?token|auth[_-]?token|"
    r"client[_-]?secret|signing[_-]?secret|secret[_-]?key|encryption[_-]?key|"
    r"private[_-]?key|session[_-]?key|secret|password|passwd|pwd|"
    r"authorization|token)"
)

# `(?<![A-Za-z0-9])` and not `\b`: the lookbehind allows a leading underscore, so
# `STRAVA_CLIENT_SECRET=` matches while `mysecret=` still does not.
_KEY_PREFIX = r"(?i)(?<![A-Za-z0-9])"

# Ordered: the URL-credentials rule runs before the email rule, or
# `user:pass@host.tld` is eaten by the email pattern and the host is lost.
_REDACT_PATTERNS = [
    (re.compile(r"xox[baprse]-[A-Za-z0-9-]{1,256}"), _MASK),               # Slack tokens
    (re.compile(r"xapp-[0-9]-[A-Za-z0-9-]{1,256}"), _MASK),               # Slack app tokens
    (re.compile(r"github_pat_[A-Za-z0-9_]{1,256}"), _MASK),               # GitHub fine-grained PATs
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{1,256}"), _MASK),                 # GitHub tokens
    (re.compile(r"sk-[A-Za-z0-9-]{16,256}"), _MASK),                      # OpenAI/Anthropic keys
    (re.compile(r"AIza[0-9A-Za-z_-]{16,256}"), _MASK),                    # Google API keys
    (re.compile(r"ya29\.[0-9A-Za-z._-]{10,512}"), _MASK),                 # Google OAuth tokens
    (re.compile(r"1//[0-9A-Za-z._-]{10,512}"), _MASK),                    # Google refresh tokens
    # `[ \t]` and not `\s`: `\s` crosses a newline and eats the first word of
    # the next traceback line.
    (re.compile(r"(?i)(bearer[ \t]{1,8})[A-Za-z0-9._-]{1,4096}"), r"\1" + _MASK),
    (re.compile(r"eyJ[A-Za-z0-9._-]{10,4096}"), _MASK),                   # JWTs
    # The lookahead keeps redaction idempotent: `token=[REDACTED]` would
    # otherwise match again on the next pass and grow a bracket each time.
    (re.compile(_KEY_PREFIX + r"(" + _SECRET_KEY + r")(['\"]?\s{0,4}[=:]\s{0,4}['\"]?)"
                r"(?!\[REDACTED\])([^\s\"',;&)}\]]{1,4096})"),
     r"\1\2" + _MASK),                                                    # key=value credentials
    # An OAuth authorization code is a live credential, exchangeable for an
    # access and a refresh token, and the three callbacks are GET routes whose
    # full path uvicorn access-logs. Query-string only: a bare `code` key would
    # swallow every `status_code=200`.
    (re.compile(r"(?i)([?&]code=)(?!\[REDACTED\])([^\s&\"']{1,4096})"), r"\1" + _MASK),
    # Userinfo with or without a password. Redacting the whole userinfo keeps
    # the host, which is the part a connection failure needs; leaving the
    # passwordless form to the email rule below erased the host instead.
    (re.compile(r"(?i)(?<![A-Za-z0-9])([a-z][a-z0-9+.-]{0,31}://)"
                r"[^\s:@/]{1,128}(?::[^\s@/]{1,256})?@"),
     r"\1" + _MASK + "@"),                                                # credentials in a URL
    (re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}"), _MASK),  # emails
]

# Chatty third parties. Root moves from "no handler at all" to INFO here, which
# would otherwise switch on every library's INFO stream at once - and urllib3 at
# DEBUG logs raw request headers. Pinned to WARNING unless the app is asking for
# something quieter still.
_NOISY_LOGGERS = (
    "apscheduler",
    "asyncio",
    "httpcore",
    "httpx",
    "openai",
    "qdrant_client",
    "sentence_transformers",
    "urllib3",
    "watchfiles",
)


def redact(text: str) -> str:
    """Mask every credential shape and email address in `text`."""
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# Kept private under its original name; `redact` is the public spelling.
_redact = redact


def _redact_arg(arg: object) -> object:
    """Redact a `%`-style argument without breaking its format spec.

    A str is redacted in place. Anything else (an exception, a dict) is only
    replaced by its redacted text when redaction actually changed something, so
    an int behind a `%d` stays an int.

    `str(arg)` runs inside `Logger.handle`, outside logging's own `emit`
    try/except, so an argument whose `__str__` raises would take down the caller
    rather than the log line. It is handed back untouched instead.
    """
    if isinstance(arg, str):
        return redact(arg)

    try:
        text = str(arg)
    except Exception:
        return arg

    redacted = redact(text)
    return redacted if redacted != text else arg


class RedactionFilter(logging.Filter):
    """Redact a record before any handler formats it."""

    def filter(self, record: logging.LogRecord) -> bool:
        # With args present, `record.msg` is the format string, and redacting it
        # can mask a placeholder sitting in the value position of a secret key
        # ("refresh token=%s expired"). That corrupts the substitution: the line
        # is dropped and logging's handleError prints the raw args to stderr,
        # which is the one path no filter or formatter can reach. Format strings
        # are developer literals; only the arguments carry runtime values, and
        # the formatter pass still redacts the finished line either way.
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(_redact_arg(a) for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: _redact_arg(v) for k, v in record.args.items()}
            return True

        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        elif record.msg is not None:
            record.msg = _redact_arg(record.msg)

        return True


class RedactingFormatter(logging.Formatter):
    """Redact the formatted line, tracebacks included.

    Wraps the formatter a handler already had, so a third-party handler keeps
    its own layout and only gains the redaction pass.
    """

    def __init__(self, inner: logging.Formatter | None = None, fmt: str | None = None):
        super().__init__(fmt)
        self._inner = inner

    def format(self, record: logging.LogRecord) -> str:
        formatted = self._inner.format(record) if self._inner else super().format(record)
        return redact(formatted)


def _harden_handler(handler: logging.Handler) -> None:
    if not any(isinstance(f, RedactionFilter) for f in handler.filters):
        handler.addFilter(RedactionFilter())
    if not isinstance(handler.formatter, RedactingFormatter):
        handler.setFormatter(RedactingFormatter(inner=handler.formatter))


def _harden_logger(logger: logging.Logger) -> None:
    # Both levels are needed. A logger filter does not run for records that
    # propagate up from a child logger, so the handler filter is what actually
    # covers a record from `uvicorn.error` reaching a handler on `uvicorn`; the
    # logger filter is what cleans `record.msg` for anything that reads the
    # record instead of formatting it (a Sentry-style logging integration).
    if not any(isinstance(f, RedactionFilter) for f in logger.filters):
        logger.addFilter(RedactionFilter())
    for handler in logger.handlers:
        _harden_handler(handler)


def _resolve_level(level: int | str | None) -> int:
    """`LOG_LEVEL` when the caller passes nothing, INFO when neither is usable.

    NOTSET is treated as INFO rather than passed through: on the root logger it
    means "log everything", which switches on every library's DEBUG stream.
    """
    if level is None:
        level = os.environ.get("LOG_LEVEL", "").strip() or logging.INFO

    if isinstance(level, str):
        resolved = int(level) if level.isdigit() else logging.getLevelName(level.upper())
    else:
        resolved = level

    if not isinstance(resolved, int) or resolved <= logging.NOTSET:
        return logging.INFO
    return resolved


def configure_logging(level: int | str | None = None) -> None:
    """Install the redacting root handler and harden every logger already set up.

    Idempotent: calling it twice does not stack filters or double-wrap a
    formatter, so an import-time call plus a later one is safe.

    The sweep over existing loggers is what covers uvicorn and gunicorn, which
    configure their own handlers with `propagate = False` before the app module
    is imported. A record leaving through one of those handlers never reaches
    the root handler installed here, so the filter has to be on those handlers
    too.
    """
    resolved = _resolve_level(level)

    handler = logging.StreamHandler()
    handler.setFormatter(
        RedactingFormatter(fmt="%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.setLevel(resolved)
    root.handlers = [handler]

    for name in list(logging.root.manager.loggerDict):
        existing = logging.root.manager.loggerDict.get(name)
        if isinstance(existing, logging.Logger) and existing.handlers:
            _harden_logger(existing)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(max(resolved, logging.WARNING))
