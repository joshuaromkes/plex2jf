"""Sync state tracking models."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Set
from pydantic import BaseModel, Field

from .media_item import MediaItem
from .user_mapping import UserMapping


class UserSyncState(BaseModel):
    """Sync state for a specific user."""
    
    plex_username: str
    last_plex_watchlist: Set[str] = Field(default_factory=set, description="Set of unique keys from last sync")
    last_seerr_requests: Set[str] = Field(default_factory=set, description="Set of unique keys from last sync")
    last_sync_time: Optional[datetime] = Field(None, description="Last successful sync time")
    
    class Config:
        json_encoders = {
            set: list,
            datetime: lambda v: v.isoformat() if v else None
        }


class SyncState(BaseModel):
    """Global sync state for all users."""
    
    user_states: dict[str, UserSyncState] = Field(default_factory=dict)
    
    def get_user_state(self, plex_username: str) -> UserSyncState:
        """Get or create sync state for a user."""
        if plex_username not in self.user_states:
            self.user_states[plex_username] = UserSyncState(plex_username=plex_username)
        return self.user_states[plex_username]
    
    def save(self, filepath: Path) -> None:
        """Save sync state to file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.model_dump(), f, indent=2, default=str)
    
    @classmethod
    def load(cls, filepath: Path) -> "SyncState":
        """Load sync state from file."""
        if not filepath.exists():
            return cls()
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Convert lists back to sets
        for user_state in data.get('user_states', {}).values():
            user_state['last_plex_watchlist'] = set(user_state.get('last_plex_watchlist', []))
            user_state['last_seerr_requests'] = set(user_state.get('last_seerr_requests', []))
        
        return cls(**data)
