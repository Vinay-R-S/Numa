def create_task_payload(title: str, user_id: str) -> dict:
    return {"title": title, "status": "planned", "user_id": user_id}


def create_calendar_payload(title: str, task_id: str) -> dict:
    return {"summary": title, "linked_task_id": task_id}


def test_integration_task_to_calendar_payload_contract():
    task = create_task_payload("Prepare presentation", "user-123")
    calendar_event = create_calendar_payload(task["title"], "task-456")

    assert calendar_event["summary"] == task["title"]
    assert calendar_event["linked_task_id"] == "task-456"
