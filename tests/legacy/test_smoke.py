def health_response() -> dict:
    return {"status": "ok"}


def app_metadata() -> dict:
    return {"name": "Numa API", "version": "1.0.0"}


def test_smoke_health_status_is_ok():
    assert health_response()["status"] == "ok"


def test_smoke_app_metadata_is_available():
    assert app_metadata()["name"] == "Numa API"


def test_smoke_version_is_non_empty():
    assert app_metadata()["version"]
