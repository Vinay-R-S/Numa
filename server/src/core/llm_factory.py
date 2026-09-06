"""
LLM Factory - unified multi-provider adapter for NUMA agents.

Supported providers: groq, openai, anthropic, gemini, ollama.

Usage::

    from src.llm_factory import get_llm, is_any_llm_configured

    llm = get_llm(user_id="...", temperature=0.1)
    llm = get_llm(provider="openai", model="gpt-4o", api_key="sk-...")

When *user_id* is supplied the factory loads per-user settings from the
``user_ai_settings`` table (encrypted API keys, chosen provider/model).
Environment variables serve as the global fallback.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

# The cipher moved to core.security on NUMA-128 (PLAN 5.1 / 8), which is where
# security.py always said it belonged. Re-exported so callers importing it from
# here - ai_settings did until this branch - keep working.
from .security import (  # noqa: F401  re-exported for existing import paths
    EncryptionKeyError,
    decrypt_api_key,
    encrypt_api_key,
)

log = logging.getLogger(__name__)

# Every provider call used to have no deadline (NUMA-139 P6, PLAN 9). A hung
# socket to Groq or Ollama held a worker thread and its pooled DB connection for
# as long as the peer kept the TCP session open, and the caller waiting on it -
# an agent route, the day planner, the Slack webhook's background task - waited
# with it. langchain's own default is no timeout, so this has to be passed.
# Read at call time, not import time, so a deployment can change it without a
# code change.
_DEFAULT_LLM_TIMEOUT = 60.0

# Ollama gets its own, much longer default. The others are hosted APIs that
# answer in seconds; Ollama is a local model that may have to be paged off disk
# before it emits a first token, and the value reaches httpx as a *read*
# timeout, so for a non-streaming call it bounds the whole generation. A 60s
# deadline would turn a slow-but-working 7B-on-CPU answer into a ReadTimeout.
_DEFAULT_OLLAMA_TIMEOUT = 300.0


def _timeout_from_env(name: str, default: float) -> float:
    raw = os.getenv(name, "")
    try:
        value = float(raw)
    except ValueError:
        return default
    # Zero or negative means "no deadline" to httpx, which is the bug this
    # closes; treat it as unset rather than honouring it.
    return value if value > 0 else default


# Built on first use and reused: the base class lives in langchain_core, and
# this module keeps every langchain import lazy so importing it stays cheap.
_feedback_handler_class = None


def _rate_limiter_callbacks(provider: str) -> list:
    """A callback that tells the rate limiter how each provider call went.

    `record_success` and `record_failure` had no call sites anywhere in the
    server, so `consecutive_failures` never moved, `circuit_open_until` was
    never set, and `_is_circuit_open` always answered False. A provider that
    started refusing every request kept being handed back at full quota and the
    fallback chain `get_llm_with_fallback` exists to provide could never fire
    (NUMA-142 P6, PLAN 9).

    Attached as a constructor kwarg rather than through `with_config`, because
    that returns a RunnableBinding and the agents call `bind_tools` on this
    object. Nothing here may raise: a bookkeeping failure must not take down the
    model call it is observing.
    """
    global _feedback_handler_class

    if _feedback_handler_class is None:
        try:
            from langchain_core.callbacks import BaseCallbackHandler
        except Exception:
            log.debug("langchain_core callbacks unavailable; rate-limiter feedback is off")
            return []

        class _RateLimiterFeedback(BaseCallbackHandler):
            def __init__(self, provider_name: str):
                self.provider_name = provider_name

            def on_llm_end(self, response, **kwargs) -> None:
                try:
                    from .rate_limiter import rate_limiter
                    output = getattr(response, "llm_output", None) or {}
                    usage = output.get("token_usage") or output.get("usage") or {}
                    tokens = int(usage.get("total_tokens") or 0)
                    rate_limiter.record_success(self.provider_name, tokens_used=tokens)
                except Exception:
                    log.debug("Rate-limiter success feedback failed", exc_info=True)

            def on_llm_error(self, error, **kwargs) -> None:
                try:
                    from .rate_limiter import rate_limiter
                    text = str(error).lower()
                    if not _is_capacity_error(text):
                        # The circuit breaker exists for a provider that cannot
                        # take the call right now. A retired model id, an
                        # over-long context or a bad key is the request's fault
                        # and repeats no matter which provider answers, so
                        # recording it would open the breaker for every user of
                        # this process (NUMA-142 P6 review).
                        return
                    rate_limiter.record_failure(
                        self.provider_name,
                        is_rate_limit=_is_rate_limit_error(text),
                    )
                except Exception:
                    log.debug("Rate-limiter failure feedback failed", exc_info=True)

        _feedback_handler_class = _RateLimiterFeedback

    return [_feedback_handler_class(provider)]


# Text that means "this provider cannot take the call right now": a 429, a
# transport failure, or a 5xx. Anything else - a bad model id, an over-long
# prompt, an invalid key - is a property of the request and must not open the
# circuit breaker for everyone (NUMA-142 P6 review).
_RATE_LIMIT_MARKERS = (
    "429",
    "rate limit",
    "rate_limit",
    "too many requests",
    "quota exceeded",
    "resource_exhausted",
)

_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "connection error",
    "connection reset",
    "connection refused",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "internal server error",
    " 500",
    " 502",
    " 503",
    " 504",
    "overloaded",
    "apiconnectionerror",
)


def _is_rate_limit_error(text: str) -> bool:
    return any(marker in text for marker in _RATE_LIMIT_MARKERS)


def _is_capacity_error(text: str) -> bool:
    if _is_rate_limit_error(text):
        return True
    # `insufficient_quota` is a permanent billing state, not back-pressure:
    # retrying elsewhere is right, but zeroing this provider's buckets is not.
    if "insufficient_quota" in text:
        return False
    return any(marker in text for marker in _TRANSIENT_MARKERS)


def _llm_timeout() -> float:
    """Per-request deadline for a hosted provider call, in seconds."""
    return _timeout_from_env("LLM_TIMEOUT_SECONDS", _DEFAULT_LLM_TIMEOUT)


def _ollama_timeout() -> float:
    """Per-request deadline for a local Ollama call, in seconds."""
    return _timeout_from_env("OLLAMA_TIMEOUT_SECONDS", _DEFAULT_OLLAMA_TIMEOUT)


SUPPORTED_PROVIDERS = ("groq", "openai", "anthropic", "gemini", "ollama")

PROVIDER_MODELS: dict[str, list[str]] = {
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-guard-3-8b",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1-mini",
    ],
    "anthropic": [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307",
        "claude-3-opus-20240229",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    "ollama": [
        "llama3.1",
        "llama3",
        "mistral",
        "phi3",
        "gemma2",
        "codellama",
    ],
}

DEFAULT_MODELS: dict[str, str] = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.1",
}

_ENV_KEY_MAP: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}

_ENV_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "groq": ("GROQ_API_KEYS", "GROQ_API_KEY"),
    "openai": ("OPENAI_API_KEYS", "OPENAI_API_KEY"),
    "anthropic": ("ANTHROPIC_API_KEYS", "ANTHROPIC_API_KEY"),
    "gemini": ("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEYS", "GOOGLE_API_KEY"),
}


def _split_api_keys(value: Optional[str]) -> list[str]:
    """Parse one or more comma-separated API keys from settings or env."""
    if not value:
        return []

    keys: list[str] = []
    for part in str(value).split(","):
        key = part.strip().strip('"').strip("'")
        if key and not _is_placeholder_key(key):
            keys.append(key)
    return keys


def _is_placeholder_key(value: str) -> bool:
    key = (value or "").strip().strip('"').strip("'")
    lowered = key.lower()
    if lowered in {
        "",
        "your_api_key",
        "your-api-key",
        "your_openai_key",
        "your_openai_api_key",
        "openai_api_key",
        "your_groq_api_key",
        "groq_api_key",
        "your_anthropic_api_key",
        "anthropic_api_key",
        "your_gemini_api_key",
        "google_api_key",
    }:
        return True
    return lowered.startswith("your-") or lowered.startswith("your_") or "-your-" in lowered


def _get_env_api_keys(provider: str) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for env_var in _ENV_KEY_ALIASES.get(provider, ()):
        for key in _split_api_keys(os.getenv(env_var, "")):
            if key not in seen:
                keys.append(key)
                seen.add(key)
    return keys


def _first_env_api_key(provider: str) -> Optional[str]:
    keys = _get_env_api_keys(provider)
    return keys[0] if keys else None


def _provider_api_keys(provider: str, api_key: Optional[str]) -> list[str]:
    keys = _split_api_keys(api_key)
    if keys:
        return keys
    return _get_env_api_keys(provider)


def _load_user_settings(user_id: str) -> Optional[dict]:
    """Fetch the active AI settings row for a user."""
    try:
        from .db import _get_conn
        conn = _get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT provider, model_id, encrypted_api_key, ollama_base_url, temperature
                FROM public.user_ai_settings
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            cur.close()
            if not row:
                return None
            return {
                "provider": row[0],
                "model_id": row[1],
                "encrypted_api_key": row[2],
                "ollama_base_url": row[3],
                "temperature": row[4],
            }
        finally:
            conn.close()
    except Exception as exc:
        log.debug("Could not load user AI settings: %s", exc)
        return None


def _resolve_provider_and_model(
    provider: Optional[str],
    model: Optional[str],
    user_id: Optional[str],
) -> tuple[str, str, Optional[str], Optional[str], Optional[float]]:
    """
    Returns (provider, model, api_key, ollama_base_url, temperature).
    Priority: explicit args → user DB settings → env vars.
    """
    api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    temperature: Optional[float] = None

    if user_id and not provider:
        settings = _load_user_settings(user_id)
        if settings and settings["provider"]:
            provider = settings["provider"]
            model = model or settings.get("model_id")
            if settings.get("encrypted_api_key"):
                try:
                    api_key = decrypt_api_key(settings["encrypted_api_key"])
                except EncryptionKeyError as exc:
                    # A configuration fault, not a bad row: every user is
                    # affected and the shared env key is about to be used in
                    # place of theirs, so say so at error level.
                    log.error("Cannot decrypt stored API keys: %s", exc)
                except Exception:
                    log.warning("Failed to decrypt API key for user %s", user_id)
            ollama_base_url = settings.get("ollama_base_url")
            temperature = settings.get("temperature")

    if not provider:
        for p in ("groq", "openai", "anthropic", "gemini"):
            keys = _get_env_api_keys(p)
            if keys:
                provider = p
                api_key = api_key or ",".join(keys)
                break

    provider = (provider or "groq").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    model = model or os.getenv(f"{provider.upper()}_MODEL", DEFAULT_MODELS.get(provider, ""))
    if not model:
        model = DEFAULT_MODELS[provider]

    if not api_key and provider != "ollama":
        keys = _get_env_api_keys(provider)
        api_key = ",".join(keys) if keys else None

    return provider, model, api_key, ollama_base_url, temperature


def get_llm(
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    user_id: Optional[str] = None,
    temperature: Optional[float] = None,
    ollama_base_url: Optional[str] = None,
):
    """
    Build and return a LangChain chat model for the resolved provider.

    Priority chain: explicit kwargs → user DB row → environment variables.
    """
    p, m, resolved_key, resolved_ollama_url, resolved_temp = _resolve_provider_and_model(
        provider, model, user_id,
    )
    final_key = api_key or resolved_key
    final_temp = temperature if temperature is not None else (resolved_temp if resolved_temp is not None else 0.1)
    final_ollama_url = ollama_base_url or resolved_ollama_url
    timeout = _llm_timeout()
    feedback = _rate_limiter_callbacks(p)

    if p == "groq":
        from langchain_groq import ChatGroq
        keys = _provider_api_keys(p, final_key)
        if not keys:
            raise RuntimeError("GROQ_API_KEY is not configured")
        llms = [
            ChatGroq(
                model=m, temperature=final_temp, api_key=key, timeout=timeout,
                callbacks=feedback,
            )
            for key in keys
        ]
        return llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]

    if p == "openai":
        from langchain_openai import ChatOpenAI
        keys = _provider_api_keys(p, final_key)
        if not keys:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        llms = [
            ChatOpenAI(
                model=m, temperature=final_temp, api_key=key, timeout=timeout,
                callbacks=feedback,
            )
            for key in keys
        ]
        return llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]

    if p == "anthropic":
        from langchain_anthropic import ChatAnthropic
        keys = _provider_api_keys(p, final_key)
        if not keys:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        llms = [
            ChatAnthropic(
                model=m, temperature=final_temp, api_key=key, timeout=timeout,
                callbacks=feedback,
            )
            for key in keys
        ]
        return llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]

    if p == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        keys = _provider_api_keys(p, final_key)
        if not keys:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        llms = [
            ChatGoogleGenerativeAI(
                model=m, temperature=final_temp, google_api_key=key, timeout=timeout,
                callbacks=feedback,
            )
            for key in keys
        ]
        return llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]

    if p == "ollama":
        from langchain_ollama import ChatOllama
        base = final_ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=m, temperature=final_temp, base_url=base,
            # ChatOllama has no timeout field of its own; this reaches the
            # underlying ollama client, which passes it to httpx.
            client_kwargs={"timeout": _ollama_timeout()},
            callbacks=feedback,
        )

    raise ValueError(f"Unsupported provider: {p}")


def is_any_llm_configured(user_id: Optional[str] = None) -> bool:
    """Check whether at least one LLM provider has valid credentials."""
    if user_id:
        settings = _load_user_settings(user_id)
        if settings and settings.get("provider"):
            if settings["provider"] == "ollama":
                return True
            if settings.get("encrypted_api_key"):
                return True

    for p in ("groq", "openai", "anthropic", "gemini"):
        key = _first_env_api_key(p)
        if key:
            return True

    return False


def get_available_providers() -> list[dict]:
    """Return a list of providers with their configuration status."""
    result = []
    for p in SUPPORTED_PROVIDERS:
        configured = False
        if p == "ollama":
            configured = True
        else:
            configured = bool(_get_env_api_keys(p))

        result.append({
            "id": p,
            "name": p.capitalize() if p != "openai" else "OpenAI",
            "configured_via_env": configured,
            "models": PROVIDER_MODELS.get(p, []),
            "default_model": DEFAULT_MODELS.get(p, ""),
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# RATE-LIMITED LLM WITH PROVIDER FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

ROUTING_MODELS: dict[str, str] = {
    "groq": os.getenv("ROUTING_MODEL_GROQ", "llama-3.1-8b-instant"),
    "openai": os.getenv("ROUTING_MODEL_OPENAI", "gpt-4o-mini"),
    "anthropic": os.getenv("ROUTING_MODEL_ANTHROPIC", "claude-3-haiku-20240307"),
    "gemini": os.getenv("ROUTING_MODEL_GEMINI", "gemini-2.0-flash"),
    "ollama": os.getenv("ROUTING_MODEL_OLLAMA", "llama3"),
}


def get_llm_with_fallback(
    *,
    user_id: Optional[str] = None,
    agent_name: str = "master",
    priority: str = "normal",
    model: Optional[str] = None,
    temperature: Optional[float] = None,
):
    """
    Get an LLM instance with rate-limit awareness and automatic fallback.

    1. Resolve the user's preferred provider
    2. Check rate limiter for capacity
    3. If exhausted, fall back to next available provider
    4. Return the LLM instance for the available provider

    Falls back to the standard ``get_llm()`` if rate limiting is unavailable.
    """
    try:
        from .rate_limiter import rate_limiter, Priority as P
    except Exception:
        log.debug("Rate limiter unavailable, using standard get_llm()")
        return get_llm(user_id=user_id, model=model, temperature=temperature)

    # Map priority string to enum
    priority_map = {"low": P.LOW, "normal": P.NORMAL, "high": P.HIGH}
    prio = priority_map.get(priority, P.NORMAL)

    # Resolve user's preferred provider
    p, m, resolved_key, resolved_ollama_url, resolved_temp = _resolve_provider_and_model(
        None, model, user_id,
    )

    # Ask rate limiter which provider to use (may fall back)
    actual_provider = rate_limiter.wait_and_acquire(
        preferred_provider=p,
        estimated_tokens=500,
        priority=prio,
        max_wait=15.0,
    )

    if actual_provider is None:
        log.warning(
            "All providers exhausted for agent '%s' - using preferred '%s' anyway",
            agent_name, p,
        )
        actual_provider = p

    # If we fell back to a different provider, use that provider's default model
    if actual_provider != p:
        log.info(
            "Agent '%s' falling back: %s -> %s",
            agent_name, p, actual_provider,
        )
        # The caller's model belongs to the preferred provider; carrying it over
        # to a different one asks for a model that does not exist there. Keep it
        # only when the fallback provider actually offers it (NUMA-142 P6).
        final_model = (
            model
            if model and model in PROVIDER_MODELS.get(actual_provider, [])
            else DEFAULT_MODELS.get(actual_provider, "")
        )
        return get_llm(
            provider=actual_provider,
            model=final_model,
            user_id=user_id,
            # The stored api key belongs to the preferred provider, so it is
            # deliberately not carried over; the user's temperature and Ollama
            # host are provider-independent and were being dropped.
            temperature=temperature if temperature is not None else resolved_temp,
            ollama_base_url=resolved_ollama_url if actual_provider == "ollama" else None,
        )

    # Use the originally resolved provider
    return get_llm(
        provider=p,
        model=m,
        api_key=resolved_key,
        user_id=user_id,
        temperature=temperature if temperature is not None else resolved_temp,
        ollama_base_url=resolved_ollama_url,
    )


def get_routing_llm(user_id: Optional[str] = None):
    """
    Get a lightweight LLM for routing/planning decisions.

    Uses a smaller, faster model (e.g. llama-3.1-8b-instant on Groq)
    to save tokens on routing decisions that don't need full model quality.
    """
    p, _, resolved_key, resolved_ollama_url, resolved_temp = _resolve_provider_and_model(
        None, None, user_id,
    )

    routing_model = ROUTING_MODELS.get(p, DEFAULT_MODELS.get(p, ""))

    return get_llm_with_fallback(
        user_id=user_id,
        agent_name="router",
        priority="normal",
        model=routing_model,
        temperature=0.0,  # routing should be deterministic
    )

