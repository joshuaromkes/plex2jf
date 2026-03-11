"""Seerr API client."""
import logging
from typing import Optional, Dict, Any, List

import requests

logger = logging.getLogger(__name__)


class SeerrClient:
    """Client for interacting with Seerr API."""
    
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json',
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Seerr API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response JSON or None on error
        """
        url = f"{self.url}/api/v1{endpoint}"
        
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Seerr API request failed: {e}")
            return None
    
    def create_request(
        self,
        media_type: str,
        media_id: int,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Create a media request.
        
        Args:
            media_type: 'movie' or 'tv'
            media_id: TMDB ID for movies, TVDB ID for TV
            user_id: Seerr user ID
            
        Returns:
            Request data if successful, None otherwise
        """
        payload = {
            'mediaType': media_type,
            'mediaId': media_id,
            'userId': user_id,
        }
        
        result = self._make_request('POST', '/request', json=payload)
        
        if result:
            logger.info(f"Created {media_type} request (ID: {media_id}) for user {user_id}")
            return result
        
        logger.error(f"Failed to create request for {media_type} ID {media_id}")
        return None
    
    def test_connection(self) -> None:
        """Test connection to Seerr. Raises exception if failed."""
        result = self._make_request('GET', '/auth/me')
        if result is None:
            raise Exception("Failed to connect to Seerr")

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all Seerr users.
        
        Returns:
            List of user dictionaries
        """
        result = self._make_request('GET', '/user')
        if result is None:
            return []
        # Seerr returns paginated results
        return result.get('results', [])

    def get_request(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Get request details.
        
        Args:
            request_id: Request ID
            
        Returns:
            Request data if found, None otherwise
        """
        return self._make_request('GET', f'/request/{request_id}')
    
    def get_users(self) -> list:
        """Get list of Seerr users.
        
        Returns:
            List of user dictionaries
        """
        result = self._make_request('GET', '/user')
        if result and 'results' in result:
            return result['results']
        return []
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User data if found, None otherwise
        """
        users = self.get_users()
        for user in users:
            if user.get('username') == username or user.get('email') == username:
                return user
        return None
    
    def health_check(self) -> bool:
        """Check if Seerr connection is healthy."""
        result = self._make_request('GET', '/status')
        if result:
            logger.debug(f"Seerr version: {result.get('version', 'Unknown')}")
            return True
        return False