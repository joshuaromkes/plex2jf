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


def test_get_user_requests(seerr_client, monkeypatch):
    """Test getting requests for a specific user."""
    requests = [
        {
            "id": 1,
            "requestedBy": {"id": 10},
            "status": 2,  # APPROVED
            "media": {"status": 5, "isAvailable": True},
        },
        {
            "id": 2,
            "requestedBy": {"id": 10},
            "status": 1,  # PENDING
            "media": {"status": 2},
        },
        {
            "id": 3,
            "requestedBy": {"id": 20},
            "status": 2,
            "media": {"status": 5},
        },
    ]

    monkeypatch.setattr(seerr_client, "get_requests", lambda: requests)

    result = seerr_client.get_user_requests(user_id=10)
    assert len(result) == 2
    assert {r["id"] for r in result} == {1, 2}

    result_with_status = seerr_client.get_user_requests(user_id=10, statuses=["APPROVED"])
    assert len(result_with_status) == 1
    assert result_with_status[0]["id"] == 1

    result_with_multiple = seerr_client.get_user_requests(user_id=10, statuses=["APPROVED", "AVAILABLE"])
    assert len(result_with_multiple) == 1
    assert result_with_multiple[0]["id"] == 1


def test_get_completed_requests(seerr_client, monkeypatch):
    """Test getting completed requests for a user."""
    requests = [
        {
            "id": 1,
            "requestedBy": {"id": 10},
            "status": 2,  # APPROVED
            "media": {"status": 5, "isAvailable": True},
        },
        {
            "id": 2,
            "requestedBy": {"id": 10},
            "status": 1,  # PENDING
            "media": {"status": 2},
        },
        {
            "id": 3,
            "requestedBy": {"id": 10},
            "status": 2,
            "media": {"status": 4},  # PARTIALLY_AVAILABLE
        },
        {
            "id": 4,
            "requestedBy": {"id": 20},
            "status": 2,
            "media": {"status": 5},
        },
    ]

    monkeypatch.setattr(seerr_client, "get_requests", lambda: requests)

    result = seerr_client.get_completed_requests(user_id=10)
    assert len(result) == 2
    assert {r["id"] for r in result} == {1, 3}

    result_user20 = seerr_client.get_completed_requests(user_id=20)
    assert len(result_user20) == 1
    assert result_user20[0]["id"] == 4


def test_extract_status_tokens(seerr_client):
    """Test status token extraction."""
    request = {
        "status": 2,
        "requestStatus": "APPROVED",
        "media": {
            "status": 5,
            "statusText": "AVAILABLE",
            "isAvailable": True,
        }
    }
    tokens = seerr_client._extract_status_tokens(request)
    assert "APPROVED" in tokens
    assert "AVAILABLE" in tokens
    assert "5" in tokens  # numeric status also included
    assert "2" in tokens

    request2 = {
        "status": "PENDING",
        "media": {}
    }
    tokens2 = seerr_client._extract_status_tokens(request2)
    assert "PENDING" in tokens2


def test_normalize_status_token(seerr_client):
    """Test status token normalization."""
    assert seerr_client._normalize_status_token(2) == "2"
    assert seerr_client._normalize_status_token("APPROVED") == "APPROVED"
    assert seerr_client._normalize_status_token(None) is None
    assert seerr_client._normalize_status_token(2, {2: "APPROVED"}) == "APPROVED"


def test_search_media(seerr_client, monkeypatch):
    """Test Seerr media search helper."""
    captured = {}

    def fake_make_request(method, endpoint, **kwargs):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["params"] = kwargs.get("params")
        return {
            "results": [
                {"id": 101, "mediaType": "movie", "title": "Fight Club", "year": 1999},
            ]
        }

    monkeypatch.setattr(seerr_client, "_make_request", fake_make_request)

    result = seerr_client.search_media(query="Fight Club", media_type="movie", year=1999)

    assert captured["method"] == "GET"
    assert captured["endpoint"] == "/search"
    assert captured["params"] == {
        "query": "Fight Club",
        "mediaType": "movie",
        "year": "1999",
    }
    assert len(result) == 1
    assert result[0]["id"] == 101


def test_search_media_handles_list_response(seerr_client, monkeypatch):
    """Test media search helper with list-shaped API responses."""
    monkeypatch.setattr(
        seerr_client,
        "_make_request",
        lambda method, endpoint, **kwargs: [
            {"id": 202, "mediaType": "tv", "title": "Good Witch", "year": 2015}
        ],
    )

    result = seerr_client.search_media(query="Good Witch", media_type="tv")

    assert len(result) == 1
    assert result[0]["id"] == 202


def test_search_media_retries_without_optional_filters(seerr_client, monkeypatch):
    """Retry query-only when Seerr rejects optional /search filters."""
    calls = []

    def fake_make_request(method, endpoint, **kwargs):
        params = kwargs.get("params") or {}
        calls.append((method, endpoint, params))

        # Simulate a deployment that rejects mediaType/year on /search.
        if "mediaType" in params or "year" in params:
            return None

        return {
            "results": [
                {"id": 303, "mediaType": "movie", "title": "Snow Bear"},
            ]
        }

    monkeypatch.setattr(seerr_client, "_make_request", fake_make_request)

    result = seerr_client.search_media(query="Snow Bear", media_type="movie", year=2020)

    assert len(calls) == 2
    assert calls[0][2] == {"query": "Snow Bear", "mediaType": "movie", "year": "2020"}
    assert calls[1][2] == {"query": "Snow Bear"}
    assert len(result) == 1
    assert result[0]["id"] == 303
