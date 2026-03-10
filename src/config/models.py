"""Configuration data models."""
from typing import List, Optional
from pydantic import BaseModel, Field


class PlexConfig(BaseModel):
    """Plex configuration."""
    url: str = Field(default="https://plex.tv", description="Plex server URL")
    token: str = Field(description="Plex admin token")


class JellyfinConfig(BaseModel):
    """Jellyfin configuration."""
    url: str = Field(description="Jellyfin server URL")
    api_key: str = Field(description="Jellyfin API key")


class SeerrConfig(BaseModel):
    """Seerr configuration."""
    url: str = Field(description="Seerr server URL")
    api_key: str = Field(description="Seerr API key")


class UserMapping(BaseModel):
    """User mapping between Plex, Jellyfin, and Seerr."""
    plex_username: str = Field(description="Plex username")
    plex_user_id: Optional[str] = Field(default=None, description="Plex user ID (optional)")
    jellyfin_user_id: str = Field(description="Jellyfin user ID")
    seerr_user_id: str = Field(description="Seerr user ID")


class SyncFeatures(BaseModel):
    """Feature flags for sync operations."""
    seerr_to_jellyfin: bool = Field(default=True, description="Sync Seerr requests to Jellyfin favorites")
    plex_watchlist_to_seerr: bool = Field(default=True, description="Sync Plex watchlist to Seerr requests")
    plex_watchlist_to_jellyfin: bool = Field(default=True, description="Sync Plex watchlist to Jellyfin favorites")


class SyncConfig(BaseModel):
    """Sync configuration."""
    polling_interval: int = Field(default=300, description="Polling interval in seconds")
    enable_webhooks: bool = Field(default=True, description="Enable webhook endpoints")
    webhook_port: int = Field(default=8000, description="Webhook server port")
    features: SyncFeatures = Field(default_factory=SyncFeatures)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    file: Optional[str] = Field(default="/data/plex2jf.log", description="Log file path")


class Config(BaseModel):
    """Main configuration model."""
    plex: PlexConfig
    jellyfin: JellyfinConfig
    seerr: SeerrConfig
    user_mappings: List[UserMapping] = Field(default_factory=list)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
