"""Tests for front status endpoint."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    import app.routers.front as front_module

    front_module._cache = None
    front_module._cache_timestamp = None
    yield
    front_module._cache = None
    front_module._cache_timestamp = None


def test_front_status_returns_valid_contract():
    """Test front status returns FrontStatusV1 contract."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/front/status")

    assert response.status_code == 200
    data = response.json()

    # Validate contract structure
    assert "updatedAt" in data
    assert "services" in data
    assert isinstance(data["services"], list)

    # Validate ISO 8601 timestamp
    datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00"))

    # Validate services structure
    for service in data["services"]:
        assert "id" in service
        assert "label" in service
        assert "state" in service
        assert service["state"] in ["ok", "warn", "down", "unknown"]


def test_front_status_loads_stub_data():
    """Test front status correctly loads data from stub."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/front/status")

    assert response.status_code == 200
    data = response.json()

    # Should have services from stub
    assert len(data["services"]) > 0

    # Check for expected services from stub
    service_ids = [s["id"] for s in data["services"]]
    assert "k8s-cluster" in service_ids


def test_front_status_caching():
    """Test front status implements caching."""
    app = create_app()
    client = TestClient(app)

    # First call - cache miss
    response1 = client.get("/front/status")
    assert response1.status_code == 200

    # Second call - should hit cache
    response2 = client.get("/front/status")
    assert response2.status_code == 200

    # Should return same data
    assert response1.json() == response2.json()


def test_front_status_fallback_on_missing_stub(tmp_path):
    """Test fallback behavior when stub is missing."""
    # Create app with non-existent stub path
    with patch("app.config.settings.stub_path", str(tmp_path / "nonexistent.json")):
        app = create_app()
        client = TestClient(app)

        # First call should fail (no cache available)
        response = client.get("/front/status")
        assert response.status_code == 500


def test_front_status_cache_ttl(tmp_path):
    """Test cache TTL configuration is respected."""
    # Create temporary stub
    stub_path = tmp_path / "status.stub.json"
    stub_data = {
        "updatedAt": "2025-11-11T16:05:00Z",
        "services": [{"id": "test-service", "label": "Test Service", "state": "ok"}],
    }

    with open(stub_path, "w") as f:
        json.dump(stub_data, f)

    # Create app with custom stub path and 0 TTL (always miss)
    with patch("app.config.settings.stub_path", str(stub_path)):
        with patch("app.config.settings.cache_ttl_seconds", 0):
            app = create_app()
            client = TestClient(app)

            # Both calls should fetch fresh data
            response1 = client.get("/front/status")
            response2 = client.get("/front/status")

            assert response1.status_code == 200
            assert response2.status_code == 200


def test_front_status_degraded_mode_detection():
    """Test degraded mode is detected when services have non-ok states."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/front/status")
    assert response.status_code == 200

    data = response.json()

    # Check if any service is not "ok" (stub has "warn" for taskboard)
    has_issues = any(s["state"] != "ok" for s in data["services"])

    # The stub should have at least one non-ok service
    assert has_issues is True


def test_metrics_endpoint():
    """Test metrics endpoint returns Prometheus format."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    # Should contain some metrics
    content = response.text
    assert "axv_gw" in content or "python" in content
