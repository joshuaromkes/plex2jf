"""Jellyfin API client."""
import logging
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)


class JellyfinClient:
    """Client for interacting with Jellyfin API."""
    
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            'X-MediaBrowser-Token': api_key,
            'Content-Type': 'application/json',
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Jellyfin API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response JSON or None on error
        """
        url = f"{self.url}{endpoint}"
        
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Jellyfin API request failed: {e}")
            return None
    
    def search_by_tmdb_id(self, tmdb_id: str, media_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Search for item by TMDB ID.
        
        Args:
            tmdb_id: TMDB ID
            media_type: 'Movie' or 'Series' (optional)
            
        Returns:
            Item data if found, None otherwise
        """
        params = {
            'Recursive': 'true',
            'AnyProviderIdEquals': f'tmdb.{tmdb_id}',
        }
        
        if media_type:
            params['IncludeItemTypes'] = media_type
        else:
            params['IncludeItemTypes'] = 'Movie,Series'
        
        result = self._make_request('GET', '/Items', params=params)
        
        if result and result.get('Items'):
            items = result['Items']
            if items:
                logger.debug(f"Found item in Jellyfin: {items[0].get('Name')} (TMDB: {tmdb_id})")
                return items[0]
        
        logger.debug(f"Item not found in Jellyfin (TMDB: {tmdb_id})")
        return None
    
    def test_connection(self) -> None:
        """Test connection to Jellyfin. Raises exception if failed."""
        result = self._make_request('GET', '/System/Info')
        if result is None:
            raise Exception("Failed to connect to Jellyfin")

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all Jellyfin users.
        
        Returns:
            List of user dictionaries
        """
        result = self._make_request('GET', '/Users')
        if result is None:
            return []
        return result

    def favorite_item(self, user_id: str, item_id: str) -> bool:
        """Mark item as favorite for user.
        
        Args:
            user_id: Jellyfin user ID
            item_id: Jellyfin item ID
            
        Returns:
            True if successful, False otherwise
        """
        result = self._make_request(
            'POST',
            f'/Users/{user_id}/FavoriteItems/{item_id}'
        )
        
        if result is not None:
            logger.info(f"Favorited item {item_id} for user {user_id}")
            return True
        
        logger.error(f"Failed to favorite item {item_id} for user {user_id}")
        return False

    def is_item_favorited(
        self,
        user_id: str,
        tmdb_id: str,
        media_type: Optional[str] = None,
    ) -> bool:
        """Check whether an item is already favorited by a user.

        Args:
            user_id: Jellyfin user ID
            tmdb_id: TMDB ID
            media_type: Optional Jellyfin item type ('Movie' or 'Series')

        Returns:
            True if favorited, False otherwise
        """
        params = {
            'Recursive': 'true',
            'Filters': 'IsFavorite',
            'AnyProviderIdEquals': f'tmdb.{tmdb_id}',
            'Limit': '1',
        }

        if media_type:
            params['IncludeItemTypes'] = media_type
        else:
            params['IncludeItemTypes'] = 'Movie,Series'

        result = self._make_request('GET', f'/Users/{user_id}/Items', params=params)
        if not result:
            return False

        items = result.get('Items', []) if isinstance(result, dict) else []
        return len(items) > 0
    
    def unfavorite_item(self, user_id: str, item_id: str) -> bool:
        """Remove item from favorites for user.
        
        Args:
            user_id: Jellyfin user ID
            item_id: Jellyfin item ID
            
        Returns:
            True if successful, False otherwise
        """
        result = self._make_request(
            'DELETE',
            f'/Users/{user_id}/FavoriteItems/{item_id}'
        )
        
        if result is not None:
            logger.info(f"Unfavorited item {item_id} for user {user_id}")
            return True
        
        logger.error(f"Failed to unfavorite item {item_id} for user {user_id}")
        return False
    
    def health_check(self) -> bool:
        """Check if Jellyfin connection is healthy."""
        result = self._make_request('GET', '/System/Info')
        if result:
            logger.debug(f"Jellyfin server: {result.get('ServerName', 'Unknown')}")
            return True
        return False
