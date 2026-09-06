def is_supported_provider(provider: str) -> bool:
    return provider in {"groq", "openai", "anthropic", "gemini", "ollama"}


def default_calendar_color(color: str | None) -> str:
    return color or "#3b82f6"


def test_sanity_default_ai_provider_is_supported():
    assert is_supported_provider("groq")


def test_sanity_unknown_ai_provider_is_not_supported():
    assert not is_supported_provider("unknown")


def test_sanity_calendar_color_has_default():
    assert default_calendar_color(None) == "#3b82f6"
