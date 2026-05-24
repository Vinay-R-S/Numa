def build_home_greeting(user: dict) -> str:
    name = user.get("full_name") or user["email"]
    return f"Welcome, {name}!"


def test_regression_home_greeting_falls_back_to_email():
    user = {"email": "student@example.com", "full_name": ""}

    assert build_home_greeting(user) == "Welcome, student@example.com!"
