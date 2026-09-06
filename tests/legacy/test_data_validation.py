def validate_temperature(value: float) -> float:
    if value < 0.0 or value > 2.0:
        raise ValueError("Temperature must be between 0.0 and 2.0")
    return value


def validate_calendar_time_range(start_time: str, end_time: str) -> tuple[str, str]:
    if end_time <= start_time:
        raise ValueError("End time must be after start time")
    return start_time, end_time


def test_data_validation_accepts_valid_temperature():
    assert validate_temperature(0.7) == 0.7


def test_data_validation_rejects_high_temperature():
    try:
        validate_temperature(2.1)
    except ValueError as exc:
        assert str(exc) == "Temperature must be between 0.0 and 2.0"
    else:
        raise AssertionError("Expected high temperature to fail")


def test_data_validation_calendar_end_must_be_after_start():
    try:
        validate_calendar_time_range("15:00", "14:00")
    except ValueError as exc:
        assert str(exc) == "End time must be after start time"
    else:
        raise AssertionError("Expected invalid time range to fail")
