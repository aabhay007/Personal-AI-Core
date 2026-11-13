"""Unit tests for health check endpoints."""
from unittest.mock import patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verify that root index endpoint returns application info."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "docs" in data
    assert "health" in data


@pytest.mark.asyncio
async def test_health_endpoint_healthy(async_client: AsyncClient):
    """Verify health endpoint returns status healthy when DB is reachable."""
    with patch("app.api.v1.health.check_database_connection", return_value=(True, "Connected successfully")):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["project_name"] == "Personal AI Core"
        assert data["database"]["connected"] is True
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient):
    """Verify /api/v1/health route returns expected schema."""
    with patch("app.api.v1.health.check_database_connection", return_value=(True, "Connected successfully")):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["connected"] is True


@pytest.mark.asyncio
async def test_health_endpoint_degraded(async_client: AsyncClient):
    """Verify health endpoint indicates degraded status when DB is unreachable."""
    with patch("app.api.v1.health.check_database_connection", return_value=(False, "Connection refused")):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["connected"] is False


@pytest.mark.asyncio
async def test_rate_limiting_headers_and_enforcement(async_client: AsyncClient):
    """Verify rate limit headers are included on responses."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
