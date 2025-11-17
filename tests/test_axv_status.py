"""
Unit Tests dla /axv/status endpoint [K4.1]

Run: pytest test_axv_status.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response, ConnectError, TimeoutException
from app.axv_status_endpoint import (
    calculate_overall_status,
    check_api_health,
    check_gateway_health,
    check_n8n_health,
    check_rag_health,
    router,
)
from fastapi.testclient import TestClient
from fastapi import FastAPI

# ============================================================================
# Test Setup
# ============================================================================

@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


# ============================================================================
# Test calculate_overall_status
# ============================================================================

def test_calculate_overall_status_all_ok():
    """Test: wszystkie komponenty OK → ok=True, overall=None"""
    status_dict = {
        "api": "ok",
        "gateway": "ok",
        "n8n": "ok",
        "rag": "ok",
    }
    ok, overall = calculate_overall_status(status_dict)
    assert ok is True
    assert overall is None


def test_calculate_overall_status_with_unknown():
    """Test: OK + unknown → ok=True, overall=None"""
    status_dict = {
        "api": "ok",
        "gateway": "ok",
        "n8n": "unknown",
        "rag": "unknown",
    }
    ok, overall = calculate_overall_status(status_dict)
    assert ok is True
    assert overall is None


def test_calculate_overall_status_degraded():
    """Test: jeden degraded → ok=True, overall=degraded"""
    status_dict = {
        "api": "ok",
        "gateway": "degraded",
        "n8n": "ok",
        "rag": "unknown",
    }
    ok, overall = calculate_overall_status(status_dict)
    assert ok is True
    assert overall == "degraded"


def test_calculate_overall_status_down():
    """Test: jeden down → ok=False, overall=None"""
    status_dict = {
        "api": "ok",
        "gateway": "ok",
        "n8n": "down",
        "rag": "ok",
    }
    ok, overall = calculate_overall_status(status_dict)
    assert ok is False
    assert overall is None


def test_calculate_overall_status_multiple_issues():
    """Test: down ma priorytet nad degraded"""
    status_dict = {
        "api": "degraded",
        "gateway": "down",
        "n8n": "ok",
        "rag": "ok",
    }
    ok, overall = calculate_overall_status(status_dict)
    assert ok is False
    assert overall is None


# ============================================================================
# Test Health Check Functions
# ============================================================================

@pytest.mark.asyncio
async def test_check_api_health_ok():
    """Test: API health check returns ok"""
    status = await check_api_health()
    # W podstawowej implementacji zawsze zwraca "ok"
    assert status == "ok"


@pytest.mark.asyncio
async def test_check_gateway_health_ok():
    """Test: Gateway responds with 200"""
    with patch("app.axv_status_endpoint.httpx.AsyncClient") as mock_client:
        mock_response = Response(200, json={"status": "ok"})
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        status = await check_gateway_health()
        assert status == "ok"


@pytest.mark.asyncio
async def test_check_gateway_health_degraded_timeout():
    """Test: Gateway timeout → degraded"""
    with patch("app.axv_status_endpoint.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=TimeoutException("Timeout")
        )
        
        status = await check_gateway_health()
        assert status == "degraded"


@pytest.mark.asyncio
async def test_check_gateway_health_down():
    """Test: Gateway connection error → down"""
    with patch("app.axv_status_endpoint.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=ConnectError("Connection refused")
        )
        
        status = await check_gateway_health()
        assert status == "down"


@pytest.mark.asyncio
async def test_check_gateway_health_server_error():
    """Test: Gateway 500 error → down"""
    with patch("app.axv_status_endpoint.httpx.AsyncClient") as mock_client:
        mock_response = Response(500, json={"error": "Internal server error"})
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        status = await check_gateway_health()
        assert status == "down"


@pytest.mark.asyncio
async def test_check_n8n_health_unknown():
    """Test: n8n bez URL → unknown"""
    with patch("app.axv_status_endpoint.N8N_HEALTHZ_URL", ""):
        status = await check_n8n_health()
        assert status == "unknown"


@pytest.mark.asyncio
async def test_check_rag_health_unknown():
    """Test: RAG stub → unknown"""
    status = await check_rag_health()
    assert status == "unknown"


# ============================================================================
# Test Full Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_get_axv_status_all_ok(client):
    """Test: pełny endpoint z wszystkimi komponentami OK"""
    with patch("app.axv_status_endpoint.check_api_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_gateway_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_n8n_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_rag_health", return_value="ok"), \
         patch("app.axv_status_endpoint.get_nodes_status", return_value=[]):
        
        response = client.get("/axv/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert "now" in data
        assert "ok" in data
        assert "version" in data
        assert "status" in data
        assert "nodes" in data
        
        # Validate values
        assert data["ok"] is True
        assert data["overall_status"] is None
        assert data["status"]["api"] == "ok"
        assert data["status"]["gateway"] == "ok"
        assert data["status"]["n8n"] == "ok"
        assert data["status"]["rag"] == "ok"
        assert isinstance(data["nodes"], list)


@pytest.mark.asyncio
async def test_get_axv_status_degraded(client):
    """Test: jeden komponent degraded → ok=True, overall_status=degraded"""
    with patch("app.axv_status_endpoint.check_api_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_gateway_health", return_value="degraded"), \
         patch("app.axv_status_endpoint.check_n8n_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_rag_health", return_value="unknown"), \
         patch("app.axv_status_endpoint.get_nodes_status", return_value=[]):
        
        response = client.get("/axv/status")
        data = response.json()
        
        assert data["ok"] is True
        assert data["overall_status"] == "degraded"
        assert data["status"]["gateway"] == "degraded"


@pytest.mark.asyncio
async def test_get_axv_status_down(client):
    """Test: jeden komponent down → ok=False"""
    with patch("app.axv_status_endpoint.check_api_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_gateway_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_n8n_health", return_value="down"), \
         patch("app.axv_status_endpoint.check_rag_health", return_value="ok"), \
         patch("app.axv_status_endpoint.get_nodes_status", return_value=[]):
        
        response = client.get("/axv/status")
        data = response.json()
        
        assert data["ok"] is False
        assert data["status"]["n8n"] == "down"


@pytest.mark.asyncio
async def test_get_axv_status_with_nodes(client):
    """Test: endpoint z listą nodów"""
    mock_nodes = [
        {
            "id": "aster",
            "role": "edge",
            "host": "asus",
            "ok": True,
            "status": "ok",
            "age_s": 12,
            "last_seen": 1762714225
        },
        {
            "id": "claude",
            "role": "compute",
            "host": "vps",
            "ok": True,
            "status": "ok",
            "age_s": 8,
            "last_seen": 1762714229
        }
    ]
    
    with patch("app.axv_status_endpoint.check_api_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_gateway_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_n8n_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_rag_health", return_value="ok"), \
         patch("app.axv_status_endpoint.get_nodes_status", return_value=mock_nodes):
        
        response = client.get("/axv/status")
        data = response.json()
        
        assert len(data["nodes"]) == 2
        assert data["nodes"][0]["id"] == "aster"
        assert data["nodes"][1]["id"] == "claude"


# ============================================================================
# Test Response Schema
# ============================================================================

def test_response_has_required_fields(client):
    """Test: response zawiera wszystkie wymagane pola"""
    with patch("app.axv_status_endpoint.check_api_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_gateway_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_n8n_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_rag_health", return_value="ok"), \
         patch("app.axv_status_endpoint.get_nodes_status", return_value=[]):
        
        response = client.get("/axv/status")
        data = response.json()
        
        # Required fields
        required_fields = ["now", "ok", "version", "status", "nodes"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Required status keys
        required_status_keys = ["api", "gateway", "n8n", "rag"]
        for key in required_status_keys:
            assert key in data["status"], f"Missing status key: {key}"
        
        # Valid status values
        valid_statuses = {"ok", "degraded", "down", "unknown"}
        for key, value in data["status"].items():
            assert value in valid_statuses, f"Invalid status value: {value}"


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
async def test_endpoint_responds_quickly(client):
    """Test: endpoint odpowiada szybko (<3s total)"""
    import time
    
    with patch("app.axv_status_endpoint.check_api_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_gateway_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_n8n_health", return_value="ok"), \
         patch("app.axv_status_endpoint.check_rag_health", return_value="ok"), \
         patch("app.axv_status_endpoint.get_nodes_status", return_value=[]):
        
        start = time.time()
        response = client.get("/axv/status")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 3.0, f"Endpoint too slow: {elapsed}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
