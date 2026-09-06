"""Signed, expiring OAuth `state` values (NUMA-142 P6, PLAN 8).

`state` is the CSRF token of an OAuth 2 flow: it is the only thing tying the
provider's redirect back to the flow the app actually started. Slack carried the
raw NUMA user id there, so `/slack/callback` believed whatever account id the
caller named and wrote that workspace's tokens into it. GitHub instead kept a
module-global `dict` of nonces, which never expires entries, grows for the life
of the process, and is written in one worker and read in another.

This is the shared mechanism for both: an HMAC over the user id and an expiry.
It is stateless, so it survives a restart and works under any number of workers;
it cannot be forged without the signing secret; and it stops being valid on its
own after `_TTL_SECONDS` rather than needing a sweeper.

What it does and does not buy. Every route that issues a state is authenticated,
so a caller can only ever obtain a state for their own user id - that is what
closes the "link a workspace into a victim's row" hole. It does not bind the
flow to a particular browser, so a caller who feeds a victim their own state
link can still have the victim's workspace land in the caller's account. Closing
that needs a per-browser value to compare against, and this app authenticates
with a Bearer token in localStorage rather than a cookie, so there is nothing to
compare against yet. The short TTL is what limits that window.
"""
from __future__ import annotations

import base64
import hmac
import logging
import os
import time
from hashlib import sha256
from typing import Optional

log = logging.getLogger(__name__)

# Ten minutes: long enough to read a consent screen, short enough that a leaked
# authorization URL is not a standing capability.
_TTL_SECONDS = 600

# `|` cannot occur in a UUID, which is what every caller passes. Issuing refuses
# a user id containing it rather than letting the field boundary move.
_SEP = "|"


class OAuthStateError(Exception):
    """The signing secret is missing, so a state can be neither issued nor checked."""


def _secret() -> bytes:
    """Read the signing secret at call time, never at import.

    `auth.service` reads JWT_SECRET at import and dies without it, which is
    correct for the module that mints sessions. Importing this one must not take
    the process down; using it without a secret must still fail closed.
    """
    raw = os.getenv("JWT_SECRET", "").strip()
    if not raw:
        raise OAuthStateError("JWT_SECRET is not set, so OAuth state cannot be signed")
    return raw.encode("utf-8")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    # urlsafe_b64decode wants the padding that _b64 stripped for URL-cleanliness.
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: bytes) -> str:
    return _b64(hmac.new(_secret(), payload, sha256).digest())


def issue_state(user_id: str, *, ttl_seconds: int = _TTL_SECONDS) -> str:
    """Return a signed state carrying `user_id` and an expiry."""
    uid = (user_id or "").strip()
    if not uid:
        raise OAuthStateError("Cannot issue an OAuth state without a user id")
    if _SEP in uid:
        raise OAuthStateError("User id may not contain the state separator")

    payload = f"{uid}{_SEP}{int(time.time()) + ttl_seconds}".encode("utf-8")
    return f"{_b64(payload)}.{_sign(payload)}"


def verify_state(state: str) -> Optional[str]:
    """Return the user id a state was issued for, or None if it is not usable.

    None covers every failure the caller treats identically - unsigned, forged,
    expired, malformed, or a legacy bare user id from a flow that started before
    this change. The reason is logged; the caller gets one answer to act on.
    """
    raw = (state or "").strip()
    if not raw:
        return None

    signed, _, signature = raw.partition(".")
    if not signature:
        # A bare user id is what the old format looked like. Refusing it is the
        # point of this change, so say so rather than logging a generic failure.
        log.warning("Rejected an OAuth state with no signature")
        return None

    # `state` is an attacker-controllable query parameter, and both `_unb64` and
    # `compare_digest` reject non-ASCII by raising - the latter with a TypeError
    # that would escape as a 500 rather than the 400 every other malformed state
    # gets (NUMA-142 P6 review).
    if not raw.isascii():
        log.warning("Rejected an OAuth state with non-ASCII characters")
        return None

    try:
        payload = _unb64(signed)
        expected = _sign(payload)
        signature_matches = hmac.compare_digest(expected, signature)
    except OAuthStateError:
        raise
    except Exception:
        log.warning("Rejected a malformed OAuth state")
        return None

    # compare_digest, not `==`: a short-circuiting comparison leaks how much of
    # a guessed signature was right.
    if not signature_matches:
        log.warning("Rejected an OAuth state whose signature did not verify")
        return None

    try:
        uid, _, expiry = payload.decode("utf-8").partition(_SEP)
        expires_at = int(expiry)
    except Exception:
        log.warning("Rejected an OAuth state with an unreadable payload")
        return None

    if time.time() > expires_at:
        log.info("Rejected an expired OAuth state")
        return None

    return uid or None
