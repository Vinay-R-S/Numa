SENSITIVE_KEYS = {"api_key", "access_token", "refresh_token", "password"}


def redact_sensitive_values(payload: dict) -> dict:
    return {
        key: "***REDACTED***" if key in SENSITIVE_KEYS else value
        for key, value in payload.items()
    }


def has_bearer_token(header: str) -> bool:
    return header.startswith("Bearer ") and len(header.split(" ", 1)[1]) > 10


def enforce_allowed_origin(origin: str, allowed_origins: set[str]) -> bool:
    return origin in allowed_origins


def test_security_sensitive_values_are_redacted():
    payload = {"email": "student@example.com", "api_key": "secret-key"}

    redacted = redact_sensitive_values(payload)

    assert redacted["email"] == "student@example.com"
    assert redacted["api_key"] == "***REDACTED***"


def test_security_multiple_sensitive_values_are_redacted():
    payload = {"access_token": "a", "refresh_token": "b", "password": "c"}

    assert set(redact_sensitive_values(payload).values()) == {"***REDACTED***"}


def test_security_bearer_token_format_is_required():
    assert has_bearer_token("Bearer abcdefghijk")
    assert not has_bearer_token("Token abcdefghijk")


def test_security_disallowed_origin_is_rejected():
    allowed = {"https://numa.example.com"}

    assert enforce_allowed_origin("https://evil.example.com", allowed) is False
