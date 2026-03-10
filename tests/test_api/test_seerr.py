"""Tests for Seerr API client."""
import pytest
import respx
from httpx import Response

from src.api.seerr import SeerrClient


@pytest.fixture
def seerr_client():
    return SeerrClient("http://test-seerr:5055", "test-api-key")


@respx.mock
def test_create_request(seerr_client):
    """Test creating a media request."""
    route = respx.post("http://test-seerr:5055/api/v1/request").mock(
        return_value=Response(200, json={
            "id": 123,
            "status": 1,
        })
    )
    
    result = seerr_client.create_request("movie", 550, 1)
    
    assert result is not None
    assert result["id"] == 123
    assert route.called


@respx.mock
def test_get_users(seerr_client):
    """Test getting users."""
    route = respx.get("http://test-seerr:5055/api/v1/user").mock(
        return_value=Response(200, json={
            "results": [
                {"id": 1, "username": "testuser"},
                {"id": 2, "username": "anotheruser"},
            ]
        })
    )
    
    result = seerr_client.get_users()
    
    assert len(result) == 2
    assert result[0]["username"] == "testuser"
    assert route.called


@respx.mock
def test_health_check(seerr_client):
    """Test health check."""
    route = respx.get("http://test-seerr:5055/api/v1/status").mock(
        return_value=Response(200, json={"version": "1.0.0"})
    )
    
    result = seerr_client.health_check()
    
    assert result is True
    assert route.called