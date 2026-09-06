def success_response(data: dict) -> dict:
    return {"ok": True, "data": data, "error": None}


def error_response(message: str, status_code: int) -> dict:
    return {"ok": False, "data": None, "error": {"message": message, "status_code": status_code}}


def test_api_contract_success_response_shape():
    response = success_response({"id": "task-1"})

    assert set(response) == {"ok", "data", "error"}
    assert response["ok"] is True
    assert response["error"] is None


def test_api_contract_error_response_shape():
    response = error_response("Invalid request", 400)

    assert response["ok"] is False
    assert response["data"] is None
    assert response["error"]["status_code"] == 400


def test_api_contract_task_response_has_required_fields():
    task = {"id": "task-1", "title": "CI", "status": "planned", "position": 0}

    assert {"id", "title", "status", "position"}.issubset(task)
