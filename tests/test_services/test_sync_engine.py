"""Tests for SyncEngine service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, UserMapping, SyncState
from src.services.sync_engine import SyncEngine


class DummyPlexClient:
    pass


class DummyJellyfinClient:
    def __init__(self):
        self.search_by_tmdb_id_result = None
        self.favorite_item_result = True
        self.is_item_favorited_result = False

    def search_by_tmdb_id(self, tmdb_id, media_type=None):
        return self.search_by_tmdb_id_result

    def favorite_item(self, user_id, item_id):
        return self.favorite_item_result

    def is_item_favorited(self, user_id, tmdb_id, media_type=None):
        return self.is_item_favorited_result


class DummySeerrClient:
    def __init__(self):
        self.find_existing_request_result = None
        self.create_request_result = None
        self.get_user_requests_result = []
        self.calls = []

    def find_existing_request(self, media_type, media_id, user_id):
        self.calls.append(("find_existing_request", media_type, media_id, user_id))
        return self.find_existing_request_result

    def create_request(self, media_type, media_id, user_id):
        self.calls.append(("create_request", media_type, media_id, user_id))
        return self.create_request_result

    def get_user_requests(self, user_id, statuses=None):
        self.calls.append(("get_user_requests", user_id, statuses))
        return self.get_user_requests_result

    def get_completed_requests(self, user_id):
        self.calls.append(("get_completed_requests", user_id))
        return self.get_user_requests_result


def _build_sync_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    seerr = DummySeerrClient()
    jellyfin = DummyJellyfinClient()
    sync_engine = SyncEngine(
        db=db,
        plex_client=DummyPlexClient(),
        jellyfin_client=jellyfin,
        seerr_client=seerr,
    )
    return db, seerr, jellyfin, sync_engine


def test_sync_plex_watchlist_to_seerr_marks_existing_remote_request_as_synced():
    """Should not create duplicates when request already exists in Seerr."""
    db, seerr, jellyfin, sync_engine = _build_sync_engine()

    mapping = UserMapping(
        plex_username="jromkes",
        jellyfin_user_id="jf-1",
        seerr_user_id="5",
    )
    db.add(mapping)
    db.commit()

    seerr.find_existing_request_result = {"id": 987}

    success = sync_engine.sync_plex_watchlist_to_seerr(
        plex_username="jromkes",
        tmdb_id="550",
        media_type="movie",
        title="Fight Club",
    )

    assert success is True
    state = db.query(SyncState).filter(SyncState.user_mapping_id == mapping.id).first()
    assert state is not None
    assert state.synced_to_seerr is True
    assert state.seerr_request_id == "987"

    find_calls = [c for c in seerr.calls if c[0] == "find_existing_request"]
    create_calls = [c for c in seerr.calls if c[0] == "create_request"]
    assert len(find_calls) == 1
    assert len(create_calls) == 0

    db.close()


def test_sync_plex_watchlist_to_seerr_creates_request_when_not_existing():
    """Should create request when no existing remote request is found."""
    db, seerr, jellyfin, sync_engine = _build_sync_engine()

    mapping = UserMapping(
        plex_username="jromkes",
        jellyfin_user_id="jf-1",
        seerr_user_id="5",
    )
    db.add(mapping)
    db.commit()

    seerr.find_existing_request_result = None
    seerr.create_request_result = {"id": 123}

    success = sync_engine.sync_plex_watchlist_to_seerr(
        plex_username="jromkes",
        tmdb_id="551",
        media_type="movie",
        title="New Movie",
    )

    assert success is True

    find_calls = [c for c in seerr.calls if c[0] == "find_existing_request"]
    create_calls = [c for c in seerr.calls if c[0] == "create_request"]
    assert len(find_calls) == 1
    assert len(create_calls) == 1

    db.close()


def test_sync_seerr_completed_to_jellyfin_with_no_requests():
    """Should handle empty Seerr request list gracefully."""
    db, seerr, jellyfin, sync_engine = _build_sync_engine()

    mapping = UserMapping(
        plex_username="jromkes",
        jellyfin_user_id="jf-1",
        seerr_user_id="5",
        is_active=True,
    )
    db.add(mapping)
    db.commit()

    seerr.get_user_requests_result = []

    summary = sync_engine.sync_seerr_completed_to_jellyfin()

    assert summary["users_processed"] == 1
    assert summary["requests_seen"] == 0
    assert summary["synced"] == 0
    assert summary["pending"] == 0
    assert summary["failed"] == 0
    assert summary["skipped"] == 0

    db.close()


def test_sync_seerr_completed_to_jellyfin_with_new_request():
    """Should sync a new Seerr request to Jellyfin."""
    db, seerr, jellyfin, sync_engine = _build_sync_engine()

    mapping = UserMapping(
        plex_username="jromkes",
        jellyfin_user_id="jf-1",
        seerr_user_id="5",
        is_active=True,
    )
    db.add(mapping)
    db.commit()

    seerr.get_user_requests_result = [
        {
            "id": 100,
            "media": {
                "mediaType": "movie",
                "tmdbId": "550",
                "title": "Fight Club",
            },
            "requestedBy": {"id": 5},
            "status": 2,
        }
    ]
    jellyfin.search_by_tmdb_id_result = {"Id": "jf-item-1", "Name": "Fight Club"}
    jellyfin.favorite_item_result = True

    summary = sync_engine.sync_seerr_completed_to_jellyfin()

    assert summary["users_processed"] == 1
    assert summary["requests_seen"] == 1
    assert summary["synced"] == 1
    assert summary["pending"] == 0
    assert summary["failed"] == 0
    assert summary["skipped"] == 0

    # Verify SyncState created
    state = db.query(SyncState).filter(
        SyncState.user_mapping_id == mapping.id,
        SyncState.external_id == "550",
        SyncState.source == "seerr_request",
    ).first()
    assert state is not None
    assert state.synced_to_jellyfin is True
    assert state.jellyfin_item_id == "jf-item-1"

    db.close()


def test_sync_seerr_completed_to_jellyfin_already_favorited():
    """Should skip if item already favorited in Jellyfin."""
    db, seerr, jellyfin, sync_engine = _build_sync_engine()

    mapping = UserMapping(
        plex_username="jromkes",
        jellyfin_user_id="jf-1",
        seerr_user_id="5",
        is_active=True,
    )
    db.add(mapping)
    db.commit()

    seerr.get_user_requests_result = [
        {
            "id": 100,
            "media": {
                "mediaType": "movie",
                "tmdbId": "550",
                "title": "Fight Club",
            },
            "requestedBy": {"id": 5},
            "status": 2,
        }
    ]
    jellyfin.search_by_tmdb_id_result = {"Id": "jf-item-1", "Name": "Fight Club"}
    jellyfin.is_item_favorited_result = True  # Already favorited

    summary = sync_engine.sync_seerr_completed_to_jellyfin()

    assert summary["users_processed"] == 1
    assert summary["requests_seen"] == 1
    assert summary["synced"] == 1  # Marked as synced due to pre-check
    assert summary["pending"] == 0
    assert summary["failed"] == 0
    assert summary["skipped"] == 0

    # Verify SyncState created with synced flag
    state = db.query(SyncState).filter(
        SyncState.user_mapping_id == mapping.id,
        SyncState.external_id == "550",
        SyncState.source == "seerr_request",
    ).first()
    assert state is not None
    assert state.synced_to_jellyfin is True

    db.close()


def test_sync_seerr_completed_to_jellyfin_item_not_found():
    """Should mark as pending when item not found in Jellyfin library."""
    db, seerr, jellyfin, sync_engine = _build_sync_engine()

    mapping = UserMapping(
        plex_username="jromkes",
        jellyfin_user_id="jf-1",
        seerr_user_id="5",
        is_active=True,
    )
    db.add(mapping)
    db.commit()

    seerr.get_user_requests_result = [
        {
            "id": 100,
            "media": {
                "mediaType": "movie",
                "tmdbId": "550",
                "title": "Fight Club",
            },
            "requestedBy": {"id": 5},
            "status": 2,
        }
    ]
    jellyfin.search_by_tmdb_id_result = None  # Not found in Jellyfin

    summary = sync_engine.sync_seerr_completed_to_jellyfin()

    assert summary["users_processed"] == 1
    assert summary["requests_seen"] == 1
    assert summary["synced"] == 0
    assert summary["pending"] == 1
    assert summary["failed"] == 0
    assert summary["skipped"] == 0

    # Verify SyncState pending
    state = db.query(SyncState).filter(
        SyncState.user_mapping_id == mapping.id,
        SyncState.external_id == "550",
        SyncState.source == "seerr_request",
    ).first()
    assert state is not None
    assert state.synced_to_jellyfin is False
    assert state.retry_count == 0

    db.close()


def test_sync_seerr_completed_to_jellyfin_duplicate_requests():
    """Should deduplicate multiple requests for same media."""
    db, seerr, jellyfin, sync_engine = _build_sync_engine()

    mapping = UserMapping(
        plex_username="jromkes",
        jellyfin_user_id="jf-1",
        seerr_user_id="5",
        is_active=True,
    )
    db.add(mapping)
    db.commit()

    seerr.get_user_requests_result = [
        {
            "id": 100,
            "media": {
                "mediaType": "movie",
                "tmdbId": "550",
                "title": "Fight Club",
            },
            "requestedBy": {"id": 5},
            "status": 2,
        },
        {
            "id": 101,
            "media": {
                "mediaType": "movie",
                "tmdbId": "550",
                "title": "Fight Club (Different)",
            },
            "requestedBy": {"id": 5},
            "status": 2,
        },
    ]
    jellyfin.search_by_tmdb_id_result = {"Id": "jf-item-1", "Name": "Fight Club"}
    jellyfin.favorite_item_result = True

    summary = sync_engine.sync_seerr_completed_to_jellyfin()

    assert summary["users_processed"] == 1
    assert summary["requests_seen"] == 1  # Only first counted, second skipped
    assert summary["skipped"] >= 1  # At least one duplicate skipped

    db.close()
