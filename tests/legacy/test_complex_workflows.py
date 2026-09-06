from collections import defaultdict


def schedule_tasks(tasks: list[dict]) -> list[dict]:
    priority_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    status_rank = {"inprogress": 0, "planned": 1, "pending": 2, "completed": 3}

    return sorted(
        tasks,
        key=lambda task: (
            status_rank[task["status"]],
            priority_rank[task["priority"]],
            task["due_date"],
            task["title"],
        ),
    )


def resolve_task_dependencies(tasks: list[dict]) -> list[str]:
    task_by_id = {task["id"]: task for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()
    ordered: list[str] = []

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise ValueError("Circular dependency detected")

        visiting.add(task_id)
        for dependency_id in task_by_id[task_id].get("depends_on", []):
            if dependency_id not in task_by_id:
                raise ValueError("Missing dependency")
            visit(dependency_id)
        visiting.remove(task_id)
        visited.add(task_id)
        ordered.append(task_id)

    for task in tasks:
        visit(task["id"])

    return ordered


def merge_calendar_events(events: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str, str], dict] = {}
    for event in events:
        key = (event["title"], event["start"], event["end"])
        existing = merged.get(key)
        if existing is None:
            merged[key] = {**event, "calendar_ids": [event["calendar_id"]]}
        else:
            existing["calendar_ids"].append(event["calendar_id"])
    return list(merged.values())


def calculate_dashboard_metrics(tasks: list[dict], events: list[dict]) -> dict:
    by_status = defaultdict(int)
    by_priority = defaultdict(int)

    for task in tasks:
        by_status[task["status"]] += 1
        by_priority[task["priority"]] += 1

    return {
        "total_tasks": len(tasks),
        "open_tasks": sum(count for status, count in by_status.items() if status != "completed"),
        "completed_tasks": by_status["completed"],
        "urgent_tasks": by_priority["urgent"],
        "calendar_events": len(events),
    }


def recursive_redact(payload: object, sensitive_keys: set[str]) -> object:
    if isinstance(payload, dict):
        return {
            key: "***REDACTED***" if key in sensitive_keys else recursive_redact(value, sensitive_keys)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [recursive_redact(item, sensitive_keys) for item in payload]
    return payload


def retry_until_success(results: list[bool], max_attempts: int) -> dict:
    attempts = 0
    for result in results[:max_attempts]:
        attempts += 1
        if result:
            return {"success": True, "attempts": attempts}
    return {"success": False, "attempts": attempts}


def paginate_items(items: list[dict], page: int, page_size: int) -> dict:
    start = (page - 1) * page_size
    end = start + page_size
    total_pages = (len(items) + page_size - 1) // page_size
    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total_items": len(items),
        "total_pages": total_pages,
    }


def test_complex_scheduler_orders_by_status_priority_due_date_and_title():
    tasks = [
        {"title": "Write report", "status": "planned", "priority": "medium", "due_date": "2026-05-28"},
        {"title": "Fix auth", "status": "inprogress", "priority": "urgent", "due_date": "2026-05-25"},
        {"title": "Clean UI", "status": "planned", "priority": "high", "due_date": "2026-05-24"},
        {"title": "Archive notes", "status": "completed", "priority": "low", "due_date": "2026-05-20"},
    ]

    ordered = schedule_tasks(tasks)

    assert [task["title"] for task in ordered] == [
        "Fix auth",
        "Clean UI",
        "Write report",
        "Archive notes",
    ]


def test_complex_dependency_resolution_places_dependencies_first():
    tasks = [
        {"id": "deploy", "depends_on": ["test"]},
        {"id": "test", "depends_on": ["build"]},
        {"id": "build", "depends_on": []},
    ]

    assert resolve_task_dependencies(tasks) == ["build", "test", "deploy"]


def test_complex_dependency_resolution_detects_cycle():
    tasks = [
        {"id": "a", "depends_on": ["b"]},
        {"id": "b", "depends_on": ["a"]},
    ]

    try:
        resolve_task_dependencies(tasks)
    except ValueError as exc:
        assert str(exc) == "Circular dependency detected"
    else:
        raise AssertionError("Expected circular dependency to fail")


def test_complex_calendar_merge_deduplicates_same_time_slot():
    events = [
        {"title": "Demo", "start": "10:00", "end": "11:00", "calendar_id": "primary"},
        {"title": "Demo", "start": "10:00", "end": "11:00", "calendar_id": "work"},
        {"title": "Lunch", "start": "13:00", "end": "14:00", "calendar_id": "primary"},
    ]

    merged = merge_calendar_events(events)

    assert len(merged) == 2
    assert sorted(merged[0]["calendar_ids"]) == ["primary", "work"]


def test_complex_dashboard_metrics_aggregate_multiple_dimensions():
    tasks = [
        {"status": "completed", "priority": "low"},
        {"status": "planned", "priority": "urgent"},
        {"status": "inprogress", "priority": "urgent"},
        {"status": "pending", "priority": "medium"},
    ]
    events = [{"id": "event-1"}, {"id": "event-2"}]

    assert calculate_dashboard_metrics(tasks, events) == {
        "total_tasks": 4,
        "open_tasks": 3,
        "completed_tasks": 1,
        "urgent_tasks": 2,
        "calendar_events": 2,
    }


def test_complex_recursive_redaction_handles_nested_payloads():
    payload = {
        "user": {"email": "student@example.com", "api_key": "secret"},
        "tokens": [{"access_token": "token-1"}, {"refresh_token": "token-2"}],
    }

    redacted = recursive_redact(payload, {"api_key", "access_token", "refresh_token"})

    assert redacted["user"]["email"] == "student@example.com"
    assert redacted["user"]["api_key"] == "***REDACTED***"
    assert redacted["tokens"][0]["access_token"] == "***REDACTED***"
    assert redacted["tokens"][1]["refresh_token"] == "***REDACTED***"


def test_complex_retry_stops_after_first_success():
    result = retry_until_success([False, False, True, True], max_attempts=4)

    assert result == {"success": True, "attempts": 3}


def test_complex_pagination_returns_expected_page_metadata():
    items = [{"id": index} for index in range(1, 26)]

    page = paginate_items(items, page=2, page_size=10)

    assert [item["id"] for item in page["items"]] == [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    assert page["total_items"] == 25
    assert page["total_pages"] == 3
