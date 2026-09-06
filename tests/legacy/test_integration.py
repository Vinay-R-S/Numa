def create_task_payload(title: str, user_id: str) -> dict:
    return {"title": title, "status": "planned", "user_id": user_id}


def create_calendar_payload(title: str, task_id: str) -> dict:
    return {"summary": title, "linked_task_id": task_id}


def build_dashboard_payload(tasks: list[dict], events: list[dict]) -> dict:
    return {
        "tasks": tasks,
        "events": events,
        "counts": {"tasks": len(tasks), "events": len(events)},
    }


def sync_task_status_to_notification(task: dict) -> dict:
    return {
        "type": "task_status_changed",
        "task_title": task["title"],
        "status": task["status"],
    }


def test_integration_task_to_calendar_payload_contract():
    task = create_task_payload("Prepare presentation", "user-123")
    calendar_event = create_calendar_payload(task["title"], "task-456")

    assert calendar_event["summary"] == task["title"]
    assert calendar_event["linked_task_id"] == "task-456"


def test_integration_dashboard_combines_tasks_and_events():
    dashboard = build_dashboard_payload(
        tasks=[{"title": "Ship tests"}],
        events=[{"summary": "Demo"}],
    )

    assert dashboard["counts"] == {"tasks": 1, "events": 1}
    assert dashboard["tasks"][0]["title"] == "Ship tests"
    assert dashboard["events"][0]["summary"] == "Demo"


def test_integration_notification_receives_task_status():
    task = {"title": "Enable CI", "status": "completed"}

    notification = sync_task_status_to_notification(task)

    assert notification == {
        "type": "task_status_changed",
        "task_title": "Enable CI",
        "status": "completed",
    }


def test_integration_user_id_is_preserved_across_payloads():
    task = create_task_payload("Review workflow", "user-999")

    assert task["user_id"] == "user-999"
