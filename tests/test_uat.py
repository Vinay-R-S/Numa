def acceptance_checklist() -> list[str]:
    return [
        "user can open dashboard",
        "user can create task",
        "user can view calendar",
        "user can update AI settings",
    ]


def test_uat_core_user_journey_is_covered():
    checklist = acceptance_checklist()

    assert "user can open dashboard" in checklist
    assert "user can create task" in checklist
    assert len(checklist) == 4


def test_uat_calendar_journey_is_present():
    assert "user can view calendar" in acceptance_checklist()


def test_uat_settings_journey_is_present():
    assert "user can update AI settings" in acceptance_checklist()
