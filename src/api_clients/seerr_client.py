"""Seerr (Overseerr/Jellyseerr) API client."""

import logging
from typing import Optional, List
from datetime import datetime
import requests

from ..models.media_item import MediaItem, MediaType

logger = logging.getLogger(__name__)


class SeerrClient:
    """Client for interacting with Seerr (Overseerr/Jellyseerr)."""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize Seerr client.
        
        Args:
            base_url: Seerr server URL (e.g., http://localhost:5055)
            api_key: Seerr API key
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to Seerr API."""
        url = f"{self.base_url}/api/v1{endpoint}"
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def _post(self, endpoint: str, data: Optional[dict] = None, params: Optional[dict] = None) -> dict:
        """Make a POST request to Seerr API."""
        url = f"{self.base_url}/api/v1{endpoint}"
        
        response = self.session.post(url, json=data, params=params, timeout=30)
        response.raise_for_status()
        return response.json() if response.text else {}
    
    def get_users(self) -> List[dict]:
        """Get all Seerr users."""
        try:
            data = self._get("/user", params={'take': 1000})
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Failed to get Seerr users: {e}")
            return []
    
    def get_user_by_name(self, username: str) -> Optional[dict]:
        """Get a user by username."""
        try:
            users = self.get_users()
            for user in users:
                if user.get('plexUsername', '').lower() == username.lower():
                    return user
                if user.get('username', '').lower() == username.lower():
                    return user
                if user.get('email', '').lower() == username.lower():
                    return user
            return None
        except Exception as e:
            logger.error(f"Failed to get Seerr user {username}: {e}")
            return None
    
    def get_user_id_by_name(self, username: str) -> Optional[int]:
        """Get user ID by username."""
        user = self.get_user_by_name(username)
        return user.get('id') if user else None
    
    def get_requests(self, user_id: Optional[int] = None, 
                    status: Optional[str] = None,
                    take: int = 1000) -> List[dict]:
        """Get requests from Seerr.
        
        Args:
            user_id: Filter by user ID
            status: Filter by status (pending, approved, available, etc.)
            take: Number of results to return
            
        Returns:
            List of request objects
        """
        try:
            params = {'take': take}
            if user_id:
                params['userId'] = user_id
            if status:
                params['filter'] = status
            
            data = self._get("/request", params)
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Failed to get Seerr requests: {e}")
            return []
    
    def get_media_info(self, tmdb_id: int, media_type: MediaType) -> Optional[dict]:
        """Get media info from Seerr by TMDB ID.
        
        Args:
            tmdb_id: TMDB ID
            media_type: Type of media
            
        Returns:
            Media info if found, None otherwise
        """
        try:
            media_type_str = 'movie' if media_type == MediaType.MOVIE else 'tv'
            return self._get(f"/{media_type_str}/{tmdb_id}")
        except Exception as e:
            logger.error(f"Failed to get media info for TMDB {tmdb_id}: {e}")
            return None
    
    def create_request(self, media_item: MediaItem, user_id: int) -> bool:
        """Create a request in Seerr for a media item.
        
        Args:
            media_item: MediaItem to request
            user_id: Seerr user ID to make the request as
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not media_item.tmdb_id:
                logger.warning(f"Cannot create request without TMDB ID: {media_item}")
                return False
            
            media_type_str = 'movie' if media_item.media_type == MediaType.MOVIE else 'tv'
            
            payload = {
                'mediaType': media_type_str,
                'mediaId': media_item.tmdb_id,
                'userId': user_id
            }
            
            self._post("/request", data=payload)
            logger.info(f"Created {media_type_str} request for TMDB {media_item.tmdb_id} as user {user_id}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                logger.info(f"Request already exists for {media_item}")
                return True  # Already requested, consider this a success
            logger.error(f"Failed to create request for {media_item}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create request for {media_item}: {e}")
            return False
    
    def request_exists(self, media_item: MediaItem, user_id: Optional[int] = None) -> bool:
        """Check if a request already exists.
        
        Args:
            media_item: MediaItem to check
            user_id: Optional user ID to filter by
            
        Returns:
            True if request exists, False otherwise
        """
        try:
            requests_list = self.get_requests(user_id=user_id)
            
            for req in requests_list:
                # Match by TMDB ID
                tmdb_id = req.get('media', {}).get('tmdbId')
                if tmdb_id and tmdb_id == media_item.tmdb_id:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to check if request exists: {e}")
            return False
    
    def get_pending_requests(self, user_id: Optional[int] = None) -> List[MediaItem]:
        """Get pending requests and convert to MediaItems.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of MediaItem objects
        """
        try:
            requests_list = self.get_requests(user_id=user_id, status='pending')
            media_items = []
            
            for req in requests_list:
                media = req.get('media', {})
                media_type = MediaType.MOVIE if media.get('mediaType') == 'movie' else MediaType.TV_SHOW
                
                item = MediaItem(
                    title=media.get('title', 'Unknown'),
                    year=media.get('releaseDate', {}).get('year') if media.get('releaseDate') else None,
                    media_type=media_type,
                    tmdb_id=media.get('tmdbId'),
                    tvdb_id=media.get('tvdbId'),
                    imdb_id=None  # Not always available in request data
                )
                media_items.append(item)
            
            return media_items
            
        except Exception as e:
            logger.error(f"Failed to get pending requests: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check if Seerr server is reachable."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/status",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Seerr health check failed: {e}")
            return False
