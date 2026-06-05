"""Configuration data models."""
from typing import Optional
from pydantic import BaseModel, Field


class UserMapping(BaseModel):
    """User mapping between Plex, Jellyfin, and Seerr."""
    plex_username: str = Field(description="Plex username")
    plex_user_id: Optional[str] = Field(default=None, description="Plex user ID (optional)")
    jellyfin_user_id: str = Field(description="Jellyfin user ID")
    seerr_user_id: str = Field(description="Seerr user ID")
