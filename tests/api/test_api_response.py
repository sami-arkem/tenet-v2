from apps.api.schemas.response import ApiResponse


def test_api_response_success_shape() -> None:
    response = ApiResponse.success(
        data={"ok": True},
        request_id="req-1",
        timestamp="2026-03-19T10:00:00Z",
        run_id="run-1",
    ).model_dump()

    assert response["data"] == {"ok": True}
    assert response["meta"]["request_id"] == "req-1"
    assert response["meta"]["run_id"] == "run-1"
    assert response["error"] is None


def test_api_response_failure_shape() -> None:
    response = ApiResponse.failure(
        code="UNAUTHORIZED",
        message="Authentication required",
        request_id="req-1",
        timestamp="2026-03-19T10:00:00Z",
    ).model_dump()

    assert response["data"] is None
    assert response["error"]["code"] == "UNAUTHORIZED"
