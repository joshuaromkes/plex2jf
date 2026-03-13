"""Tests for Seerr API client."""
import pytest

from src.api.seerr import SeerrClient


@pytest.fixture
def seerr_client():
    return SeerrClient("http://test-seerr:5055", "test-api-key")


def test_create_request(seerr_client, monkeypatch):
    """Test creating a media request."""
    captured = {}

    def fake_make_request(method, endpoint, **kwargs):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["json"] = kwargs.get("json")
        return {"id": 123, "status": 1}

    monkeypatch.setattr(seerr_client, "_make_request", fake_make_request)
    
    result = seerr_client.create_request("movie", 550, 1)
    
    assert result is not None
    assert result["id"] == 123
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "/request"
    assert captured["json"]["mediaType"] == "movie"
    assert captured["json"]["mediaId"] == 550
    assert captured["json"]["userId"] == 1


def test_get_users(seerr_client, monkeypatch):
    """Test getting users."""
    def fake_make_request(method, endpoint, **kwargs):
        if endpoint == "/user?take=100&skip=0":
            return {
            "results": [
                {"id": 1, "username": "testuser"},
                {"id": 2, "username": "anotheruser"},
            ],
            "pageInfo": {"results": 2},
        }
        return {"results": []}

    monkeypatch.setattr(seerr_client, "_make_request", fake_make_request)
    
    result = seerr_client.get_users()
    
    assert len(result) == 2
    assert result[0]["username"] == "testuser"


def test_health_check(seerr_client, monkeypatch):
    """Test health check."""
    monkeypatch.setattr(
        seerr_client,
        "_make_request",
        lambda method, endpoint, **kwargs: {"version": "1.0.0"} if endpoint == "/status" else None,
    )
    
    result = seerr_client.health_check()
    
    assert result is True


def test_get_requests_paginates(seerr_client, monkeypatch):
    """Test request pagination helper."""
    responses = [
        {
            "results": [
                {"id": 1},
                {"id": 2},
            ],
            "pageInfo": {"results": 3},
        },
        {
            "results": [
                {"id": 3},
            ],
            "pageInfo": {"results": 3},
        },
    ]

    def fake_make_request(method, endpoint, **kwargs):
        if endpoint == "/request?take=2&skip=0":
            return responses[0]
        if endpoint == "/request?take=2&skip=2":
            return responses[1]
        return {"results": []}

    monkeypatch.setattr(seerr_client, "_make_request", fake_make_request)

    result = seerr_client.get_requests(take=2, max_pages=5)

    assert [r["id"] for r in result] == [1, 2, 3]


def test_find_existing_request_matches_media_and_user(seerr_client, monkeypatch):
    """Test finding an existing request by media type/id and user."""
    requests = [
        {
            "id": 10,
            "media": {"mediaType": "movie", "tmdbId": 500},
            "requestedBy": {"id": 1},
        },
        {
            "id": 20,
            "media": {"mediaType": "tv", "tmdbId": 550},
            "requestedBy": {"id": 5},
        },
    ]

    monkeypatch.setattr(seerr_client, "get_requests", lambda: requests)

    result = seerr_client.find_existing_request(media_type="tv", media_id=550, user_id=5)

    assert result is not None
    assert result["id"] == 20
