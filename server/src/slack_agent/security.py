"""Slack request signature verification (NUMA-105 P3, NUMA-129 P6, PLAN 8).

HMAC-SHA256 verification with timestamp freshness, per
https://api.slack.com/authentication/verifying-requests-from-slack

What changed on NUMA-129 is the failure behavior. An unset `SLACK_SIGNING_SECRET`
used to return True and log a warning, so `/slack/events` - the one route in the
app with no JWT dependency - accepted any unsigned POST from anywhere. Anyone who
knew the URL could forge message events into another user's history, drive the
task-extraction agent, or delete rows through a `message_deleted` payload.

Verification now fails closed: no secret, no signature, a non-numeric or stale
timestamp, or a malformed signature all reject the request. `verify_signing_secret`
turns the missing-secret case into a boot failure when Slack is configured at all,
so the fault surfaces at startup instead of as a silently open webhook.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time

from .config import SIGNING_SECRET_ENV, _signing_secret, slack_is_configured

log = logging.getLogger(__name__)

#: Slack's current signature version prefix.
SIGNATURE_VERSION = "v0"

#: Slack's own recommendation: reject anything older than five minutes.
MAX_SIGNATURE_AGE_SECONDS = 300

_SIGNATURE_RE = re.compile(rf"^{SIGNATURE_VERSION}=[0-9a-f]{{64}}$")

MISSING_SECRET_MESSAGE = (
    f"{SIGNING_SECRET_ENV} is not set. /slack/events cannot verify that a request "
    "came from Slack, so every request to it is refused. Copy the signing secret "
    "from https://api.slack.com/apps -> your app -> Basic Information."
)

__all__ = [
    "MAX_SIGNATURE_AGE_SECONDS",
    "MISSING_SECRET_MESSAGE",
    "SIGNATURE_VERSION",
    "SlackSigningSecretError",
    "signing_secret_configured",
    "verify_signing_secret",
    "verify_slack_signature",
]


class SlackSigningSecretError(RuntimeError):
    """The signing secret is missing while Slack is otherwise configured."""


def signing_secret_configured() -> bool:
    return bool(_signing_secret())


def _expected_signature(secret: str, timestamp: str, request_body: bytes) -> str:
    """Slack's `v0=<hex>` digest over the raw body.

    The base string is assembled as bytes: the body is signed exactly as it
    arrived, so a payload that is not valid UTF-8 is a signature mismatch rather
    than a decode error swallowed into a rejection.
    """
    base = f"{SIGNATURE_VERSION}:{timestamp}:".encode("utf-8") + request_body
    digest = hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_VERSION}={digest}"


def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """True only for a fresh, correctly signed Slack request.

    Every other outcome - including an unset secret - is False. Callers must not
    treat a rejection as a reason to fall back to trusting the payload.
    """
    secret = _signing_secret()
    if not secret:
        log.error("Slack request rejected: %s", MISSING_SECRET_MESSAGE)
        return False

    if not timestamp or not signature:
        log.warning("Slack request rejected: signature or timestamp header missing")
        return False

    if not _SIGNATURE_RE.match(signature):
        log.warning("Slack request rejected: malformed signature header")
        return False

    try:
        sent_at = int(timestamp)
    except ValueError:
        log.warning("Slack request rejected: non-numeric timestamp")
        return False

    age = time.time() - sent_at
    if abs(age) > MAX_SIGNATURE_AGE_SECONDS:
        log.warning(
            "Slack request rejected: timestamp is %ds off, outside the %ds window",
            int(age),
            MAX_SIGNATURE_AGE_SECONDS,
        )
        return False

    if not hmac.compare_digest(_expected_signature(secret, timestamp, request_body), signature):
        log.warning("Slack request rejected: signature mismatch")
        return False

    return True


def verify_signing_secret() -> None:
    """Boot check (PLAN 8). Raises rather than letting the fault reach the webhook.

    A missing secret fails the boot only when Slack is configured at all, the way
    NUMA-128 fails the boot only when there is ciphertext to lose: an install with
    no Slack credentials has nothing to verify, so it starts and the webhook keeps
    refusing every request.
    """
    if signing_secret_configured():
        log.info("%s is present; /slack/events is signature-verified.", SIGNING_SECRET_ENV)
        return

    if slack_is_configured():
        raise SlackSigningSecretError(
            f"{MISSING_SECRET_MESSAGE} Slack is configured, so the server will not start."
        )

    log.warning("%s Slack is not configured either.", MISSING_SECRET_MESSAGE)
