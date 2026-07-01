"""
Rate Limiter - thread-safe token-bucket rate limiting with provider fallback.

Provides centralized rate limiting for all NUMA agents so they don't
independently overwhelm LLM providers.  When the primary provider is
exhausted (429 / circuit-open) the limiter transparently falls back to
the next provider in the configured chain.

Usage::

    from src.rate_limiter import rate_limiter, Priority

    provider = rate_limiter.acquire("groq", estimated_tokens=500, priority=Priority.NORMAL)
    # provider may be "groq", "gemini", or "ollama" depending on capacity
    # ... make LLM call ...
    rate_limiter.record_success(provider, tokens_used=320)
"""
from __future__ import annotations

import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


class Priority(IntEnum):
    LOW = 0       # background tasks (sync, journal auto-gen)
    NORMAL = 1    # sub-agent delegation
    HIGH = 2      # active user chat via master agent


@dataclass
class _Bucket:
    """Token-bucket state for a single LLM provider."""
    provider: str
    rpm: int                           # max requests per minute
    tpm: int                           # max tokens per minute
    requests_remaining: int = 0
    tokens_remaining: int = 0
    window_start: float = 0.0          # monotonic timestamp
    consecutive_failures: int = 0
    circuit_open_until: Optional[float] = None  # monotonic timestamp

    def __post_init__(self):
        self.requests_remaining = self.rpm
        self.tokens_remaining = self.tpm
        self.window_start = time.monotonic()


class RateLimiter:
    """
    Thread-safe, per-provider rate limiter with automatic fallback.

    The fallback chain is configurable via ``LLM_FALLBACK_CHAIN`` env var
    (default: ``groq,gemini,ollama``).  When a provider is exhausted or
    circuit-broken the next provider in the chain is tried.
    """

    # How many consecutive failures before we open the circuit breaker
    CIRCUIT_BREAKER_THRESHOLD = 3
    # How long the circuit stays open (seconds)
    CIRCUIT_BREAKER_COOLDOWN = 60.0
    # One-minute sliding window
    WINDOW_SECONDS = 60.0

    def __init__(self) -> None:
        self._lock = threading.Lock()

        chain_raw = os.getenv("LLM_FALLBACK_CHAIN", "groq,gemini,ollama")
        self.fallback_chain: List[str] = [
            p.strip().lower() for p in chain_raw.split(",") if p.strip()
        ]

        self._buckets: Dict[str, _Bucket] = {}
        self._init_buckets()

    # ── initialisation ────────────────────────────────────────────────────────

    def _init_buckets(self) -> None:
        defaults: Dict[str, tuple] = {
            "groq":      (int(os.getenv("GROQ_RPM",      "25")),  int(os.getenv("GROQ_TPM",      "6000"))),
            "gemini":    (int(os.getenv("GEMINI_RPM",     "14")),  int(os.getenv("GEMINI_TPM",     "32000"))),
            "openai":    (int(os.getenv("OPENAI_RPM",     "500")), int(os.getenv("OPENAI_TPM",     "30000"))),
            "anthropic": (int(os.getenv("ANTHROPIC_RPM",  "50")),  int(os.getenv("ANTHROPIC_TPM",  "40000"))),
            "ollama":    (int(os.getenv("OLLAMA_RPM",     "999")), int(os.getenv("OLLAMA_TPM",     "999999"))),
        }
        for provider, (rpm, tpm) in defaults.items():
            self._buckets[provider] = _Bucket(provider=provider, rpm=rpm, tpm=tpm)

    # ── sliding window refresh ────────────────────────────────────────────────

    def _maybe_refresh(self, bucket: _Bucket) -> None:
        """Reset the bucket if the 60-second window has elapsed."""
        now = time.monotonic()
        elapsed = now - bucket.window_start
        if elapsed >= self.WINDOW_SECONDS:
            bucket.requests_remaining = bucket.rpm
            bucket.tokens_remaining = bucket.tpm
            bucket.window_start = now

    # ── circuit breaker ───────────────────────────────────────────────────────

    def _is_circuit_open(self, bucket: _Bucket) -> bool:
        if bucket.circuit_open_until is None:
            return False
        now = time.monotonic()
        if now >= bucket.circuit_open_until:
            # Cooldown elapsed → close circuit, give it another chance
            bucket.circuit_open_until = None
            bucket.consecutive_failures = 0
            log.info("Circuit breaker closed for provider '%s'", bucket.provider)
            return False
        return True

    # ── public API ────────────────────────────────────────────────────────────

    def acquire(
        self,
        preferred_provider: str,
        estimated_tokens: int = 500,
        priority: Priority = Priority.NORMAL,
    ) -> Optional[str]:
        """
        Try to acquire capacity on *preferred_provider*.  If exhausted,
        walk the fallback chain.  Returns the provider name to use, or
        ``None`` if every provider is exhausted (caller should retry later).
        """
        with self._lock:
            # Build ordered list: preferred first, then fallback chain
            candidates = [preferred_provider] + [
                p for p in self.fallback_chain if p != preferred_provider
            ]

            for provider in candidates:
                bucket = self._buckets.get(provider)
                if bucket is None:
                    continue

                if self._is_circuit_open(bucket):
                    continue

                self._maybe_refresh(bucket)

                if bucket.requests_remaining <= 0:
                    continue
                if bucket.tokens_remaining < estimated_tokens:
                    continue

                # Reserve capacity
                bucket.requests_remaining -= 1
                bucket.tokens_remaining -= estimated_tokens

                if provider != preferred_provider:
                    log.info(
                        "Rate limiter fallback: %s → %s (priority=%s)",
                        preferred_provider, provider, priority.name,
                    )

                return provider

            # All providers exhausted
            log.warning(
                "All LLM providers exhausted (preferred=%s, est_tokens=%d)",
                preferred_provider, estimated_tokens,
            )
            return None

    def wait_and_acquire(
        self,
        preferred_provider: str,
        estimated_tokens: int = 500,
        priority: Priority = Priority.NORMAL,
        max_wait: float = 30.0,
    ) -> Optional[str]:
        """
        Like :meth:`acquire` but will sleep-and-retry if no provider is
        available, up to *max_wait* seconds.  Uses exponential backoff
        with jitter.
        """
        deadline = time.monotonic() + max_wait
        attempt = 0

        while True:
            result = self.acquire(preferred_provider, estimated_tokens, priority)
            if result is not None:
                return result

            if time.monotonic() >= deadline:
                return None

            # Exponential backoff: 0.5s, 1s, 2s, 4s … capped at remaining time
            base_wait = min(0.5 * (2 ** attempt), 8.0)
            jitter = random.uniform(0, base_wait * 0.3)
            sleep_time = min(base_wait + jitter, deadline - time.monotonic())

            if sleep_time <= 0:
                return None

            log.debug("Rate limiter waiting %.1fs before retry (attempt %d)", sleep_time, attempt)
            time.sleep(sleep_time)
            attempt += 1

    def record_success(self, provider: str, tokens_used: int = 0) -> None:
        """Record a successful LLM call.  Resets the failure counter."""
        with self._lock:
            bucket = self._buckets.get(provider)
            if bucket is None:
                return
            bucket.consecutive_failures = 0

    def record_failure(self, provider: str, is_rate_limit: bool = False) -> None:
        """
        Record a failed LLM call.  If *is_rate_limit* is True or the
        failure count reaches the threshold, open the circuit breaker.
        """
        with self._lock:
            bucket = self._buckets.get(provider)
            if bucket is None:
                return
            bucket.consecutive_failures += 1

            if is_rate_limit:
                # Immediately exhaust remaining capacity for this window
                bucket.requests_remaining = 0
                bucket.tokens_remaining = 0
                log.warning(
                    "Provider '%s' rate-limited — exhausting bucket for this window",
                    provider,
                )

            if bucket.consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                bucket.circuit_open_until = (
                    time.monotonic() + self.CIRCUIT_BREAKER_COOLDOWN
                )
                log.warning(
                    "Circuit breaker OPEN for provider '%s' (%d consecutive failures, "
                    "cooldown %.0fs)",
                    provider,
                    bucket.consecutive_failures,
                    self.CIRCUIT_BREAKER_COOLDOWN,
                )

    def get_status(self) -> Dict[str, dict]:
        """Return a snapshot of all bucket states (for health endpoint)."""
        with self._lock:
            result = {}
            for name, b in self._buckets.items():
                self._maybe_refresh(b)
                result[name] = {
                    "rpm": b.rpm,
                    "tpm": b.tpm,
                    "requests_remaining": b.requests_remaining,
                    "tokens_remaining": b.tokens_remaining,
                    "circuit_open": self._is_circuit_open(b),
                    "consecutive_failures": b.consecutive_failures,
                }
            return result


# ── Module-level singleton ────────────────────────────────────────────────────

rate_limiter = RateLimiter()
