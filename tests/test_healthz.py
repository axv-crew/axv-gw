"""Tests for healthz endpoint."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_ok():
    """Test healthz endpoint returns ok status."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_healthz_multiple_calls():
    """Test healthz can be called multiple times."""
    app = create_app()
    client = TestClient(app)

    for _ in range(3):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["ok"] is True
