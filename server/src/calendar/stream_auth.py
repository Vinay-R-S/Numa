"""Short-lived tokens for the calendar SSE stream (NUMA-132 P6, PLAN 8 / 16.1).

`EventSource` cannot send an `Authorization` header, which is why
`/calendar/events/stream` had no auth at all: it was open to anyone, and the
version feed it served was process-global, so every connected browser refetched
the month whenever *any* user touched their calendar.

The stream is authenticated with a scoped token instead, minted by an
authenticated route and passed in the query string. It follows the same shape as
the Google OAuth state token in `oauth.py`: same secret, a `scope` claim, and a
short expiry. Two properties make putting it in a URL acceptable:

- It expires in two minutes, and is only read when a stream is opened.
- It is not a session token. `get_current_user` refuses any token carrying a
  `scope` claim, so this one opens a stream and nothing else.

Stateless on purpose: an in-memory ticket store would not survive a restart and
would not match across workers, the same failure NUMA-131 documented for the
per-process watch token.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from jose import JWTError, jwt

from .config import JWT_ALGORITHM, JWT_SECRET

STREAM_TOKEN_SCOPE = "google_calendar_stream"
STREAM_TOKEN_TTL_SECONDS = 120

__all__ = [
    "STREAM_TOKEN_SCOPE",
    "STREAM_TOKEN_TTL_SECONDS",
    "build_stream_token",
    "decode_stream_token",
]


def build_stream_token(user_id: str | None) -> str:
    """Mint a stream-only token for `user_id`.

    An empty `sub` is legitimate: `_optional_user_id` yields None for a token
    without one, and that caller gets its own version bucket rather than sharing
    every other user's.
    """
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")

    now = datetime.now(UTC)
    payload = {
        "sub": user_id or "",
        "scope": STREAM_TOKEN_SCOPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=STREAM_TOKEN_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_stream_token(token: str) -> str | None:
    """The user id the token was minted for, or 401.

    A session token is rejected here just as this token is rejected as a session
    token: the scope has to match exactly, in both directions.
    """
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")

    if not token:
        raise HTTPException(status_code=401, detail="Missing stream token")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired stream token") from exc

    if payload.get("scope") != STREAM_TOKEN_SCOPE:
        raise HTTPException(status_code=401, detail="Invalid stream token scope")

    return str(payload.get("sub") or "") or None
