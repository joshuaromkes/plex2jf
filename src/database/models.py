"""Database models for plex2jf."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ServerConfig(Base):
    """Server configuration for Plex, Jellyfin, and Seerr."""
    __tablename__ = "server_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_type = Column(String, nullable=False)  # 'plex', 'jellyfin', 'seerr'
    name = Column(String, nullable=False)  # User-friendly name
    url = Column(String, nullable=False)
    api_key = Column(String, nullable=True)
    token = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String, nullable=True)  # 'success', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppSettings(Base):
    """Application settings stored in database."""
    __tablename__ = "app_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)  # JSON-encoded value
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExternalUser(Base):
    """User cache from external services (Plex, Jellyfin, Seerr)."""
    __tablename__ = "external_users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_type = Column(String, nullable=False)  # 'plex', 'jellyfin', 'seerr'
    external_id = Column(String, nullable=False)
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("service_type", "external_id", name="uix_external_user"),
    )


class UserMapping(Base):
    """User mapping between Plex, Jellyfin, and Seerr."""
    __tablename__ = "user_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plex_username = Column(String, nullable=False, unique=True)
    plex_user_id = Column(String, nullable=True)
    jellyfin_user_id = Column(String, nullable=False)
    seerr_user_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sync_states = relationship("SyncState", back_populates="user_mapping", cascade="all, delete-orphan")


class SyncState(Base):
    """Sync state tracking for media items."""
    __tablename__ = "sync_state"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_mapping_id = Column(Integer, ForeignKey("user_mappings.id"), nullable=False)
    media_type = Column(String, nullable=False)  # 'movie' or 'tv'
    external_id = Column(String, nullable=False)  # TMDB/TVDB ID
    title = Column(String, nullable=True)
    
    # Source tracking
    source = Column(String, nullable=False)  # 'plex_watchlist', 'seerr_request'
    source_id = Column(String, nullable=True)
    
    # Sync status
    synced_to_jellyfin = Column(Boolean, default=False)
    jellyfin_item_id = Column(String, nullable=True)
    synced_to_seerr = Column(Boolean, default=False)
    seerr_request_id = Column(String, nullable=True)
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # Timestamps
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
    
    # Relationships
    user_mapping = relationship("UserMapping", back_populates="sync_states")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint("user_mapping_id", "external_id", "source", name="uix_sync_state"),
    )


class WebhookEvent(Base):
    """Webhook events log."""
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)  # JSON
    processed = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class PollingState(Base):
    """Polling state tracking."""
    __tablename__ = "polling_state"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service = Column(String, nullable=False, unique=True)  # 'plex_watchlist'
    last_poll_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    error_count = Column(Integer, default=0)