def compact_dashboard_summary(tasks_count: int, events_count: int) -> dict:
    return {
        "tasks_count": tasks_count,
        "events_count": events_count,
        "total_items": tasks_count + events_count,
    }


def top_recent_items(items: list[dict], limit: int) -> list[dict]:
    return sorted(items, key=lambda item: item["created_at"], reverse=True)[:limit]


def test_performance_dashboard_summary_uses_small_payload():
    summary = compact_dashboard_summary(tasks_count=12, events_count=5)

    assert summary == {"tasks_count": 12, "events_count": 5, "total_items": 17}
    assert len(summary) <= 3


def test_performance_recent_items_are_limited():
    items = [{"id": index, "created_at": f"2026-05-{index:02d}"} for index in range(1, 21)]

    recent = top_recent_items(items, limit=5)

    assert len(recent) == 5
    assert recent[0]["id"] == 20


def test_performance_large_summary_stays_constant_size():
    summary = compact_dashboard_summary(tasks_count=1000, events_count=2000)

    assert summary["total_items"] == 3000
    assert set(summary) == {"tasks_count", "events_count", "total_items"}
