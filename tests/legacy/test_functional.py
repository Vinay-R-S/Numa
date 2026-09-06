VALID_STATUSES = {"planned", "inprogress", "completed", "pending"}


def move_task(task: dict, status: str) -> dict:
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status")
    return {**task, "status": status}


def filter_tasks_by_status(tasks: list[dict], status: str) -> list[dict]:
    return [task for task in tasks if task["status"] == status]


def mark_task_overdue(task: dict, today: str) -> dict:
    is_overdue = bool(task.get("due_date")) and task["due_date"] < today
    return {**task, "overdue": is_overdue}


def test_functional_user_can_mark_task_completed():
    task = {"title": "Enable CI", "status": "planned"}

    updated_task = move_task(task, "completed")

    assert updated_task["status"] == "completed"
    assert updated_task["title"] == "Enable CI"


def test_functional_invalid_status_is_rejected():
    try:
        move_task({"title": "Draft"}, "blocked")
    except ValueError as exc:
        assert str(exc) == "Invalid status"
    else:
        raise AssertionError("Expected invalid status to fail")


def test_functional_filters_completed_tasks():
    tasks = [
        {"title": "A", "status": "completed"},
        {"title": "B", "status": "planned"},
        {"title": "C", "status": "completed"},
    ]

    completed = filter_tasks_by_status(tasks, "completed")

    assert [task["title"] for task in completed] == ["A", "C"]


def test_functional_marks_past_due_task_overdue():
    task = mark_task_overdue({"title": "Submit", "due_date": "2026-05-20"}, "2026-05-24")

    assert task["overdue"] is True
