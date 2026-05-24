def safe_first_item(items: list[dict]) -> dict | None:
    return items[0] if items else None


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def test_edge_case_empty_list_returns_none():
    assert safe_first_item([]) is None


def test_edge_case_first_item_is_returned():
    assert safe_first_item([{"id": 1}, {"id": 2}]) == {"id": 1}


def test_edge_case_long_text_is_truncated():
    assert truncate_text("abcdef", 3) == "abc"
