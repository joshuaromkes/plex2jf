"""Media item models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """Type of media."""
    MOVIE = "movie"
    TV_SHOW = "tv"


class MediaItem(BaseModel):
    """Represents a media item (movie or TV show)."""
    
    title: str = Field(..., description="Title of the media")
    year: Optional[int] = Field(None, description="Release year")
    media_type: MediaType = Field(..., description="Type of media")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID")
    tvdb_id: Optional[int] = Field(None, description="TVDB ID")
    imdb_id: Optional[str] = Field(None, description="IMDB ID")
    plex_rating_key: Optional[str] = Field(None, description="Plex rating key")
    jellyfin_item_id: Optional[str] = Field(None, description="Jellyfin item ID")
    
    def __str__(self) -> str:
        year_str = f" ({self.year})" if self.year else ""
        return f"{self.title}{year_str} [{self.media_type.value}]"
    
    def __hash__(self) -> int:
        """Make MediaItem hashable for use in sets."""
        return hash((self.title, self.year, self.media_type, self.tmdb_id, self.imdb_id))
    
    def __eq__(self, other: object) -> bool:
        """Equality check for MediaItem."""
        if not isinstance(other, MediaItem):
            return False
        return (
            self.title == other.title and
            self.year == other.year and
            self.media_type == other.media_type and
            self.tmdb_id == other.tmdb_id and
            self.imdb_id == other.imdb_id
        )
    
    @property
    def unique_key(self) -> str:
        """Generate a unique key for this item."""
        if self.tmdb_id:
            return f"tmdb:{self.tmdb_id}"
        if self.imdb_id:
            return f"imdb:{self.imdb_id}"
        if self.tvdb_id:
            return f"tvdb:{self.tvdb_id}"
        return f"{self.title}:{self.year}:{self.media_type.value}"
