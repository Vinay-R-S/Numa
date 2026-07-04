"""Slack request signature verification (NUMA-105 P3, PLAN 16.2).

HMAC-SHA256 verification with timestamp freshness, per
https://api.slack.com/authentication/verifying-requests-from-slack
Extracted verbatim from slack_agent/router.py; router.py re-exports this name.
"""
import hashlib
import hmac
import logging
import time

from .config import _signing_secret

log = logging.getLogger(__name__)


def _verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack's HMAC-SHA256 request signature (industry-standard security)."""
    secret = _signing_secret()
    if not secret:
        # If signing secret is not configured, skip verification (dev mode)
        log.warning("SLACK_SIGNING_SECRET not configured - skipping signature check!")
        return True

    try:
        ts_int = int(timestamp)
        if abs(time.time() - ts_int) > 300:
            log.warning("Slack event timestamp too old: %s", timestamp)
            return False
        base_string = f"v0:{timestamp}:{request_body.decode('utf-8')}"
        computed    = "v0=" + hmac.new(
            secret.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)
    except Exception as exc:
        log.warning("Signature verification error: %s", exc)
        return False
