VALID_STATUSES = {"planned", "inprogress", "completed", "pending"}


def move_task(task: dict, status: str) -> dict:
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status")
    return {**task, "status": status}


def test_functional_user_can_mark_task_completed():
    task = {"title": "Enable CI", "status": "planned"}

    updated_task = move_task(task, "completed")

    assert updated_task["status"] == "completed"
    assert updated_task["title"] == "Enable CI"
