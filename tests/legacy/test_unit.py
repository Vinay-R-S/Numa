def normalize_task_title(title: str) -> str:
    return " ".join(title.strip().split())


def parse_priority(priority: str | None) -> str:
    allowed = {"low", "medium", "high", "urgent"}
    if priority is None:
        return "medium"
    normalized = priority.strip().lower()
    if normalized not in allowed:
        raise ValueError("Invalid priority")
    return normalized


def calculate_completion_rate(completed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((completed / total) * 100, 2)


def test_unit_task_title_normalization_trims_extra_spaces():
    assert normalize_task_title("  Finish   CI setup  ") == "Finish CI setup"


def test_unit_task_title_normalization():
    assert normalize_task_title("\nPrepare\tpresentation\n") == "Prepare presentation"


def test_unit_priority_defaults_to_medium():
    assert parse_priority(None) == "medium"


def test_unit_priority_rejects_unknown_value():
    try:
        parse_priority("critical")
    except ValueError as exc:
        assert str(exc) == "Invalid priority"
    else:
        raise AssertionError("Expected invalid priority to fail")


def test_unit_completion_rate_handles_zero_total():
    assert calculate_completion_rate(completed=3, total=0) == 0.0


def test_unit_completion_rate_rounds_to_two_decimals():
    assert calculate_completion_rate(completed=2, total=3) == 66.67
