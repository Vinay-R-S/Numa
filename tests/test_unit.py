def normalize_task_title(title: str) -> str:
    return " ".join(title.strip().split())


def test_unit_task_title_normalization():
    assert normalize_task_title("  Finish   CI setup  ") == "Finish CI setup"
