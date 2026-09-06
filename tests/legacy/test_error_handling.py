def parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return 0
    return parsed if parsed > 0 else 0


def get_nested_value(payload: dict, key: str, default: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) and value else default


def test_error_handling_invalid_integer_returns_zero():
    assert parse_positive_int("abc") == 0


def test_error_handling_negative_integer_returns_zero():
    assert parse_positive_int("-4") == 0


def test_error_handling_missing_nested_value_uses_default():
    assert get_nested_value({}, "title", "Untitled") == "Untitled"
