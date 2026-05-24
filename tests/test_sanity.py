def is_supported_provider(provider: str) -> bool:
    return provider in {"groq", "openai", "anthropic", "gemini", "ollama"}


def test_sanity_default_ai_provider_is_supported():
    assert is_supported_provider("groq")
