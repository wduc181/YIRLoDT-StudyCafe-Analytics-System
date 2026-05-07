"""Contract tests for API error status codes and response shape."""

from uuid import uuid4
import io

from fastapi import HTTPException
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.dependencies import get_db
from app.main import app
from app.routers import report
from app.services import session_service


async def _override_get_db():
    yield object()


def _client() -> TestClient:
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_start_session_missing_device_id_returns_contract_400() -> None:
    client = _client()
    try:
        response = client.post("/api/session/start", json={})
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 400
    assert response.json() == {
        "status": "error",
        "message": "device_id is required",
    }


def test_get_session_invalid_uuid_returns_contract_422() -> None:
    client = _client()
    try:
        response = client.get("/api/session/not-a-uuid")
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 422
    assert response.json() == {
        "status": "error",
        "message": "invalid session_id",
    }


def test_tracking_invalid_uuid_returns_contract_422() -> None:
    client = _client()
    try:
        response = client.post(
            "/api/tracking",
            json={
                "device_id": "device-001",
                "session_id": "not-a-uuid",
                "lat": 21.0,
                "lng": 105.0,
                "accuracy": 10.0,
                "timestamp": "2026-04-07T09:01:00Z",
            },
        )
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 422
    assert response.json() == {
        "status": "error",
        "message": "invalid session_id",
    }


def test_route_not_found_returns_contract_404() -> None:
    client = _client()
    try:
        response = client.get("/no-such-route")
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 404
    assert response.json() == {
        "status": "error",
        "message": "Not Found",
    }


def test_method_not_allowed_returns_contract_405() -> None:
    client = _client()
    try:
        response = client.post("/")
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 405
    assert response.json() == {
        "status": "error",
        "message": "Method Not Allowed",
    }


def test_http_exception_handler_preserves_status_and_unwraps_detail(monkeypatch) -> None:
    async def fake_end_session(_db, _request, _background_tasks):
        raise HTTPException(
            status_code=409,
            detail={"status": "error", "message": "session already ended"},
        )

    monkeypatch.setattr(session_service, "end_session", fake_end_session)
    client = _client()
    try:
        response = client.post(
            "/api/session/end",
            json={"session_id": str(uuid4())},
        )
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 409
    assert response.json() == {
        "status": "error",
        "message": "session already ended",
    }


def test_report_export_requires_internal_token(monkeypatch) -> None:
    monkeypatch.setattr(report.settings, "REPORT_EXPORT_TOKEN", "secret")
    client = _client()
    try:
        response = client.get("/api/report/export")
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 401
    assert response.json() == {
        "status": "error",
        "message": "unauthorized",
    }


def test_report_export_accepts_internal_token(monkeypatch) -> None:
    output = io.BytesIO()
    Workbook().save(output)
    output_bytes = output.getvalue()

    async def fake_generate_report(_db):
        return io.BytesIO(output_bytes)

    monkeypatch.setattr(report.settings, "REPORT_EXPORT_TOKEN", "secret")
    monkeypatch.setattr(report.report_service, "generate_report", fake_generate_report)

    client = _client()
    try:
        response = client.get(
            "/api/report/export",
            headers={"X-Internal-Token": "secret"},
        )
    finally:
        client.close()
        _clear_overrides()

    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        'attachment; filename="studycafe_report.xlsx"'
    )
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
