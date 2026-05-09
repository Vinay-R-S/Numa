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

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

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


def _get_encryption_key() -> bytes:
    """Derive or retrieve the Fernet key for API-key encryption."""
    raw = os.getenv("NUMA_ENCRYPTION_KEY", "").strip()
    if raw:
        return raw.encode()
    from cryptography.fernet import Fernet as _F
    key = _F.generate_key()
    log.warning(
        "NUMA_ENCRYPTION_KEY not set - generated ephemeral key. "
        "Set it in .env to persist encrypted API keys across restarts."
    )
    return key


_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_encryption_key())
    return _fernet


def encrypt_api_key(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()


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
                except Exception:
                    log.warning("Failed to decrypt API key for user %s", user_id)
            ollama_base_url = settings.get("ollama_base_url")
            temperature = settings.get("temperature")

    if not provider:
        for p in ("groq", "openai", "anthropic", "gemini"):
            env_var = _ENV_KEY_MAP.get(p, "")
            key = os.getenv(env_var, "").strip()
            if key and not key.lower().startswith("your_"):
                provider = p
                api_key = api_key or key
                break

    provider = (provider or "groq").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    model = model or os.getenv(f"{provider.upper()}_MODEL", DEFAULT_MODELS.get(provider, ""))
    if not model:
        model = DEFAULT_MODELS[provider]

    if not api_key and provider != "ollama":
        env_var = _ENV_KEY_MAP.get(provider, "")
        api_key = os.getenv(env_var, "").strip() or None

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

    if p == "groq":
        from langchain_groq import ChatGroq
        if not final_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        return ChatGroq(model=m, temperature=final_temp, api_key=final_key)

    if p == "openai":
        from langchain_openai import ChatOpenAI
        if not final_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        return ChatOpenAI(model=m, temperature=final_temp, api_key=final_key)

    if p == "anthropic":
        from langchain_anthropic import ChatAnthropic
        if not final_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        return ChatAnthropic(model=m, temperature=final_temp, api_key=final_key)

    if p == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not final_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        return ChatGoogleGenerativeAI(model=m, temperature=final_temp, google_api_key=final_key)

    if p == "ollama":
        from langchain_ollama import ChatOllama
        base = final_ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model=m, temperature=final_temp, base_url=base)

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
        env_var = _ENV_KEY_MAP.get(p, "")
        key = os.getenv(env_var, "").strip()
        if key and not key.lower().startswith("your_"):
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
            env_var = _ENV_KEY_MAP.get(p, "")
            key = os.getenv(env_var, "").strip()
            configured = bool(key and not key.lower().startswith("your_"))

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
            "All providers exhausted for agent '%s' — using preferred '%s' anyway",
            agent_name, p,
        )
        actual_provider = p

    # If we fell back to a different provider, use that provider's default model
    if actual_provider != p:
        log.info(
            "Agent '%s' falling back: %s → %s",
            agent_name, p, actual_provider,
        )
        final_model = model or DEFAULT_MODELS.get(actual_provider, "")
        return get_llm(
            provider=actual_provider,
            model=final_model,
            user_id=user_id,
            temperature=temperature,
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

