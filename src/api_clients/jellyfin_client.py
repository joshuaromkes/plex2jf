"""Jellyfin API client."""

import logging
from typing import Optional, List
import requests

from ..models.media_item import MediaItem, MediaType

logger = logging.getLogger(__name__)


class JellyfinClient:
    """Client for interacting with Jellyfin Media Server."""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize Jellyfin client.
        
        Args:
            base_url: Jellyfin server URL (e.g., http://localhost:8096)
            api_key: Jellyfin API key
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Emby-Token': api_key,
            'X-MediaBrowser-Token': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to Jellyfin API."""
        url = f"{self.base_url}{endpoint}"
        
        # Add API key to params if not present
        if params is None:
            params = {}
        if 'api_key' not in params:
            params['api_key'] = self.api_key
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def _post(self, endpoint: str, data: Optional[dict] = None, params: Optional[dict] = None) -> dict:
        """Make a POST request to Jellyfin API."""
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        if 'api_key' not in params:
            params['api_key'] = self.api_key
        
        response = self.session.post(url, json=data, params=params, timeout=30)
        response.raise_for_status()
        return response.json() if response.text else {}
    
    def get_users(self) -> List[dict]:
        """Get all Jellyfin users."""
        try:
            return self._get("/Users")
        except Exception as e:
            logger.error(f"Failed to get Jellyfin users: {e}")
            return []
    
    def get_user_by_name(self, username: str) -> Optional[dict]:
        """Get a user by username."""
        try:
            users = self.get_users()
            for user in users:
                if user.get('Name', '').lower() == username.lower():
                    return user
            return None
        except Exception as e:
            logger.error(f"Failed to get Jellyfin user {username}: {e}")
            return None
    
    def get_user_id_by_name(self, username: str) -> Optional[str]:
        """Get user ID by username."""
        user = self.get_user_by_name(username)
        return user.get('Id') if user else None
    
    def search_item(self, query: str, media_type: Optional[MediaType] = None, 
                  year: Optional[int] = None, limit: int = 10) -> List[dict]:
        """Search for an item in the Jellyfin library.
        
        Args:
            query: Search query (title)
            media_type: Filter by media type (movie or tv show)
            year: Filter by year
            limit: Maximum number of results
            
        Returns:
            List of matching items
        """
        try:
            params = {
                'searchTerm': query,
                'limit': limit,
                'IncludeItemTypes': ''
            }
            
            if media_type == MediaType.MOVIE:
                params['IncludeItemTypes'] = 'Movie'
            elif media_type == MediaType.TV_SHOW:
                params['IncludeItemTypes'] = 'Series'
            
            data = self._get("/Items", params)
            items = data.get('Items', [])
            
            # Filter by year if provided
            if year:
                items = [item for item in items 
                        if item.get('ProductionYear') == year or 
                        item.get('PremiereDate', '').startswith(str(year))]
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to search Jellyfin for '{query}': {e}")
            return []
    
    def find_item_by_external_id(self, tmdb_id: Optional[int] = None,
                                  tvdb_id: Optional[int] = None,
                                  imdb_id: Optional[str] = None,
                                  media_type: Optional[MediaType] = None) -> Optional[dict]:
        """Find an item by external ID (TMDB, TVDB, or IMDB).
        
        Args:
            tmdb_id: TMDB ID
            tvdb_id: TVDB ID
            imdb_id: IMDB ID
            media_type: Type of media
            
        Returns:
            Item data if found, None otherwise
        """
        try:
            # Build search params based on available IDs
            params = {'recursive': True, 'fields': 'ExternalIds'}
            
            if media_type == MediaType.MOVIE:
                params['IncludeItemTypes'] = 'Movie'
            elif media_type == MediaType.TV_SHOW:
                params['IncludeItemTypes'] = 'Series'
            
            data = self._get("/Items", params)
            items = data.get('Items', [])
            
            for item in items:
                external_ids = item.get('ExternalIds', {})
                
                if tmdb_id and str(external_ids.get('Tmdb', '')) == str(tmdb_id):
                    return item
                if tvdb_id and str(external_ids.get('Tvdb', '')) == str(tvdb_id):
                    return item
                if imdb_id and external_ids.get('Imdb') == imdb_id:
                    return item
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find item by external ID: {e}")
            return None
    
    def favorite_item(self, user_id: str, item_id: str) -> bool:
        """Favorite an item for a user.
        
        Args:
            user_id: Jellyfin user ID
            item_id: Item ID to favorite
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._post(f"/Users/{user_id}/FavoriteItems/{item_id}")
            logger.info(f"Favorited item {item_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to favorite item {item_id}: {e}")
            return False
    
    def unfavorite_item(self, user_id: str, item_id: str) -> bool:
        """Unfavorite an item for a user.
        
        Args:
            user_id: Jellyfin user ID
            item_id: Item ID to unfavorite
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/Users/{user_id}/FavoriteItems/{item_id}"
            params = {'api_key': self.api_key}
            response = self.session.delete(url, params=params, timeout=30)
            response.raise_for_status()
            logger.info(f"Unfavorited item {item_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unfavorite item {item_id}: {e}")
            return False
    
    def get_favorites(self, user_id: str) -> List[dict]:
        """Get all favorites for a user.
        
        Args:
            user_id: Jellyfin user ID
            
        Returns:
            List of favorite items
        """
        try:
            params = {
                'recursive': True,
                'filters': 'IsFavorite',
                'fields': 'ExternalIds,Path'
            }
            data = self._get(f"/Users/{user_id}/Items", params)
            return data.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get favorites for user {user_id}: {e}")
            return []
    
    def favorite_media_item(self, user_id: str, media_item: MediaItem) -> bool:
        """Favorite a media item by searching for it first.
        
        Args:
            user_id: Jellyfin user ID
            media_item: MediaItem to favorite
            
        Returns:
            True if successful, False otherwise
        """
        # First try to find by external ID
        item = self.find_item_by_external_id(
            tmdb_id=media_item.tmdb_id,
            tvdb_id=media_item.tvdb_id,
            imdb_id=media_item.imdb_id,
            media_type=media_item.media_type
        )
        
        # If not found by ID, try searching by title
        if not item:
            logger.debug(f"Item not found by ID, searching by title: {media_item.title}")
            results = self.search_item(
                query=media_item.title,
                media_type=media_item.media_type,
                year=media_item.year,
                limit=5
            )
            
            if results:
                item = results[0]  # Take the first match
                logger.debug(f"Found item by title search: {item.get('Name')}")
        
        if not item:
            logger.warning(f"Could not find item in Jellyfin: {media_item}")
            return False
        
        item_id = item.get('Id')
        if not item_id:
            logger.warning(f"Item has no ID: {item}")
            return False
        
        return self.favorite_item(user_id, item_id)
    
    def health_check(self) -> bool:
        """Check if Jellyfin server is reachable."""
        try:
            response = self.session.get(
                f"{self.base_url}/System/Info",
                params={'api_key': self.api_key},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Jellyfin health check failed: {e}")
            return False
