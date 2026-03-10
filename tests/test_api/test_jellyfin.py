"""Tests for Jellyfin API client."""
import pytest
import respx
from httpx import Response

from src.api.jellyfin import JellyfinClient


@pytest.fixture
def jellyfin_client():
    return JellyfinClient("http://test-jellyfin:8096", "test-api-key")


@respx.mock
def test_search_by_tmdb_id(jellyfin_client):
    """Test searching for item by TMDB ID."""
    # Mock the response
    route = respx.get("http://test-jellyfin:8096/Items").mock(
        return_value=Response(200, json={
            "Items": [
                {
                    "Id": "test-item-id",
                    "Name": "Test Movie",
                    "Type": "Movie",
                }
            ]
        })
    )
    
    result = jellyfin_client.search_by_tmdb_id("12345")
    
    assert result is not None
    assert result["Id"] == "test-item-id"
    assert result["Name"] == "Test Movie"
    assert route.called


@respx.mock
def test_search_by_tmdb_id_not_found(jellyfin_client):
    """Test searching for item that doesn't exist."""
    route = respx.get("http://test-jellyfin:8096/Items").mock(
        return_value=Response(200, json={"Items": []})
    )
    
    result = jellyfin_client.search_by_tmdb_id("99999")
    
    assert result is None
    assert route.called


@respx.mock
def test_favorite_item(jellyfin_client):
    """Test favoriting an item."""
    route = respx.post("http://test-jellyfin:8096/Users/user-123/FavoriteItems/item-456").mock(
        return_value=Response(200, json={})
    )
    
    result = jellyfin_client.favorite_item("user-123", "item-456")
    
    assert result is True
    assert route.called


@respx.mock
def test_health_check(jellyfin_client):
    """Test health check."""
    route = respx.get("http://test-jellyfin:8096/System/Info").mock(
        return_value=Response(200, json={"ServerName": "Test Server"})
    )
    
    result = jellyfin_client.health_check()
    
    assert result is True
    assert route.called