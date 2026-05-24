def compact_dashboard_summary(tasks_count: int, events_count: int) -> dict:
    return {
        "tasks_count": tasks_count,
        "events_count": events_count,
        "total_items": tasks_count + events_count,
    }


def test_performance_dashboard_summary_uses_small_payload():
    summary = compact_dashboard_summary(tasks_count=12, events_count=5)

    assert summary == {"tasks_count": 12, "events_count": 5, "total_items": 17}
    assert len(summary) <= 3
