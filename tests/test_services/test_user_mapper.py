"""Tests for user mapper service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, UserMapping
from src.services.user_mapper import UserMapper
from src.config.models import UserMapping as UserMappingConfig


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def user_mapper(db_session):
    return UserMapper(db_session)


def test_sync_user_mappings(user_mapper, db_session):
    """Test syncing user mappings from config."""
    mappings = [
        UserMappingConfig(
            plex_username="testuser",
            plex_user_id="123",
            jellyfin_user_id="jf-123",
            seerr_user_id="sr-123",
        )
    ]
    
    user_mapper.sync_user_mappings(mappings)
    
    result = db_session.query(UserMapping).first()
    assert result is not None
    assert result.plex_username == "testuser"
    assert result.jellyfin_user_id == "jf-123"


def test_get_mapping_by_plex_username(user_mapper, db_session):
    """Test getting mapping by Plex username."""
    # Add a mapping
    mapping = UserMapping(
        plex_username="testuser",
        jellyfin_user_id="jf-123",
        seerr_user_id="sr-123",
    )
    db_session.add(mapping)
    db_session.commit()
    
    result = user_mapper.get_mapping_by_plex_username("testuser")
    
    assert result is not None
    assert result.plex_username == "testuser"


def test_get_mapping_by_seerr_user_id(user_mapper, db_session):
    """Test getting mapping by Seerr user ID."""
    # Add a mapping
    mapping = UserMapping(
        plex_username="testuser",
        jellyfin_user_id="jf-123",
        seerr_user_id="sr-123",
    )
    db_session.add(mapping)
    db_session.commit()
    
    result = user_mapper.get_mapping_by_seerr_user_id("sr-123")
    
    assert result is not None
    assert result.seerr_user_id == "sr-123"