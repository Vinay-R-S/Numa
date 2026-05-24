SENSITIVE_KEYS = {"api_key", "access_token", "refresh_token", "password"}


def redact_sensitive_values(payload: dict) -> dict:
    return {
        key: "***REDACTED***" if key in SENSITIVE_KEYS else value
        for key, value in payload.items()
    }


def test_security_sensitive_values_are_redacted():
    payload = {"email": "student@example.com", "api_key": "secret-key"}

    redacted = redact_sensitive_values(payload)

    assert redacted["email"] == "student@example.com"
    assert redacted["api_key"] == "***REDACTED***"
