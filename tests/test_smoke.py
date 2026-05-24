def health_response() -> dict:
    return {"status": "ok"}


def test_smoke_health_status_is_ok():
    assert health_response()["status"] == "ok"
