"""Tests for SyncEngine service."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, UserMapping, SyncState
from src.services.sync_engine import SyncEngine


class DummyPlexClient:
    pass


class DummyJellyfinClient:
    pass


class DummySeerrClient:
    def __init__(self):
        self.find_existing_request_result = None
        self.create_request_result = None
        self.calls = []

    def find_existing_request(self, media_type, media_id, user_id):
        self.calls.append(("find_existing_request", media_type, media_id, user_id))
        return self.find_existing_request_result

    def create_request(self, media_type, media_id, user_id):
        self.calls.append(("create_request", media_type, media_id, user_id))
        return self.create_request_result


def _build_sync_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    seerr = DummySeerrClient()
    sync_engine = SyncEngine(
        db=db,
        plex_client=DummyPlexClient(),
        jellyfin_client=DummyJellyfinClient(),
        seerr_client=seerr,
    )
    return db, seerr, sync_engine


def test_sync_plex_watchlist_to_seerr_marks_existing_remote_request_as_synced():
    """Should not create duplicates when request already exists in Seerr."""
    db, seerr, sync_engine = _build_sync_engine()

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
    db, seerr, sync_engine = _build_sync_engine()

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

