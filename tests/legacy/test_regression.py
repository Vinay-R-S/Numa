def build_home_greeting(user: dict) -> str:
    name = user.get("full_name") or user["email"]
    return f"Welcome, {name}!"


def preserve_task_position(task: dict, updates: dict) -> dict:
    return {**task, **updates, "position": updates.get("position", task["position"])}


def test_regression_home_greeting_falls_back_to_email():
    user = {"email": "student@example.com", "full_name": ""}

    assert build_home_greeting(user) == "Welcome, student@example.com!"


def test_regression_home_greeting_prefers_full_name():
    user = {"email": "student@example.com", "full_name": "Vinay"}

    assert build_home_greeting(user) == "Welcome, Vinay!"


def test_regression_task_position_does_not_reset_on_title_edit():
    task = {"title": "Old", "position": 7, "status": "planned"}

    updated = preserve_task_position(task, {"title": "New"})

    assert updated["position"] == 7
    assert updated["title"] == "New"
