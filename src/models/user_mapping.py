"""User mapping models for linking Plex, Jellyfin, and Seerr users."""

from typing import Optional
from pydantic import BaseModel, Field


class UserMapping(BaseModel):
    """Maps a user across Plex, Jellyfin, and Seerr systems."""
    
    plex_username: str = Field(..., description="Plex username")
    jellyfin_username: str = Field(..., description="Jellyfin username")
    jellyfin_user_id: Optional[str] = Field(None, description="Jellyfin user ID (auto-populated)")
    seerr_username: str = Field(..., description="Seerr username")
    seerr_user_id: Optional[int] = Field(None, description="Seerr user ID (auto-populated)")
    
    def __str__(self) -> str:
        return f"UserMapping(plex={self.plex_username}, jellyfin={self.jellyfin_username}, seerr={self.seerr_username})"


class UserMappings(BaseModel):
    """Collection of user mappings."""
    
    mappings: list[UserMapping] = Field(default_factory=list, description="List of user mappings")
    
    def get_by_plex(self, plex_username: str) -> Optional[UserMapping]:
        """Get mapping by Plex username."""
        for mapping in self.mappings:
            if mapping.plex_username == plex_username:
                return mapping
        return None
    
    def get_by_jellyfin(self, jellyfin_username: str) -> Optional[UserMapping]:
        """Get mapping by Jellyfin username."""
        for mapping in self.mappings:
            if mapping.jellyfin_username == jellyfin_username:
                return mapping
        return None
    
    def get_by_seerr(self, seerr_username: str) -> Optional[UserMapping]:
        """Get mapping by Seerr username."""
        for mapping in self.mappings:
            if mapping.seerr_username == seerr_username:
                return mapping
        return None
    
    def get_by_seerr_id(self, seerr_user_id: int) -> Optional[UserMapping]:
        """Get mapping by Seerr user ID."""
        for mapping in self.mappings:
            if mapping.seerr_user_id == seerr_user_id:
                return mapping
        return None
