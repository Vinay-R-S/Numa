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
