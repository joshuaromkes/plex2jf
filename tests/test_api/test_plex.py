"""Tests for Plex API client."""

from src.api.plex import PlexClient, PlexGraphQLUserNotFoundError


def test_watchlistarr_includes_managed_mapped_users(monkeypatch):
    """Mapped managed users should be fetched even if missing from friends list."""
    client = PlexClient("test-token", "https://plex.tv")

    monkeypatch.setattr(client, "_get_friends_graphql", lambda: [])
    monkeypatch.setattr(client, "_get_user_uuid", lambda: "owner-uuid")
    monkeypatch.setattr(
        client,
        "get_managed_users",
        lambda: [
            {"id": "100", "uuid": "managed-uuid", "title": "Kanish Inamdar"},
        ],
    )

    fetched_users = []

    def fake_get_watchlist_for_user(username, user_id, page=None):
        fetched_users.append((username, user_id))
        return []

    monkeypatch.setattr(client, "_get_watchlist_for_user_graphql", fake_get_watchlist_for_user)

    items = client._get_watchlist_graphql_watchlistarr(
        account_username="jromkes",
        account_user_id="1",
        mapped_usernames=["jromkes", "kanishinamdar", "torymalpass"],
    )

    assert items == []
    assert ("jromkes", "owner-uuid") in fetched_users
    assert ("Kanish Inamdar", "managed-uuid") in fetched_users
    assert len(fetched_users) == 2


def test_watchlistarr_deduplicates_users_across_sources(monkeypatch):
    """A mapped user present in multiple sources should only be fetched once."""
    client = PlexClient("test-token", "https://plex.tv")

    monkeypatch.setattr(
        client,
        "_get_friends_graphql",
        lambda: [{"id": "friend-uuid", "username": "Kanish Inamdar"}],
    )
    monkeypatch.setattr(client, "_get_user_uuid", lambda: "owner-uuid")
    monkeypatch.setattr(
        client,
        "get_managed_users",
        lambda: [{"id": "100", "uuid": "managed-uuid", "title": "Kanish Inamdar"}],
    )

    fetched_users = []

    def fake_get_watchlist_for_user(username, user_id, page=None):
        fetched_users.append((username, user_id))
        return []

    monkeypatch.setattr(client, "_get_watchlist_for_user_graphql", fake_get_watchlist_for_user)

    items = client._get_watchlist_graphql_watchlistarr(
        account_username="jromkes",
        account_user_id="1",
        mapped_usernames=["kanishinamdar"],
    )

    assert items == []
    assert len(fetched_users) == 1
    assert fetched_users[0][0] == "Kanish Inamdar"


def test_watchlistarr_falls_back_to_alternate_managed_user_id_on_user_not_found(monkeypatch):
    """If one managed-user ID fails GraphQL lookup, an alternate ID candidate should be tried."""
    client = PlexClient("test-token", "https://plex.tv")

    monkeypatch.setattr(client, "_get_friends_graphql", lambda: [])
    monkeypatch.setattr(client, "_get_user_uuid", lambda: "owner-uuid")
    monkeypatch.setattr(
        client,
        "get_managed_users",
        lambda: [
            {"id": "198975710", "uuid": "bad-uuid", "title": "Tory Malpass"},
        ],
    )

    attempted_ids = []

    def fake_get_watchlist_for_user(username, user_id, page=None):
        attempted_ids.append(user_id)
        if user_id == "bad-uuid":
            raise PlexGraphQLUserNotFoundError("User not found")
        return []

    monkeypatch.setattr(client, "_get_watchlist_for_user_graphql", fake_get_watchlist_for_user)

    items = client._get_watchlist_graphql_watchlistarr(
        account_username="jromkes",
        account_user_id="1",
        mapped_usernames=["torymalpass"],
    )

    assert items == []
    assert attempted_ids == ["bad-uuid", "198975710"]
