"""Seerr API client."""
import logging
from typing import Optional, Dict, Any, List, Set

import requests

logger = logging.getLogger(__name__)


REQUEST_STATUS_MAP = {
    1: 'PENDING',
    2: 'APPROVED',
    3: 'DECLINED',
}

MEDIA_STATUS_MAP = {
    1: 'UNKNOWN',
    2: 'PENDING',
    3: 'PROCESSING',
    4: 'PARTIALLY_AVAILABLE',
    5: 'AVAILABLE',
}


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

        # Seerr expects season selection for TV requests in many deployments.
        # Without this, TV requests can fail with server-side 500 errors.
        if media_type == 'tv':
            payload['seasons'] = 'all'
        
        logger.info(f"Seerr create_request payload: {payload}")
        logger.info(f"Seerr API URL: {self.url}/api/v1/request")
        
        result = self._make_request('POST', '/request', json=payload)
        
        if result:
            logger.info(f"Created {media_type} request (ID: {media_id}) for user {user_id}, response: {result}")
            return result
        
        logger.error(f"Failed to create request for {media_type} ID {media_id} - result was None")
        return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        """Best-effort int conversion helper."""
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_requests(self, take: int = 100, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Get Seerr requests with pagination.

        Args:
            take: Page size
            max_pages: Safety limit for pagination

        Returns:
            List of request dictionaries
        """
        all_requests: List[Dict[str, Any]] = []

        for page in range(max_pages):
            skip = page * take
            result = self._make_request('GET', f'/request?take={take}&skip={skip}')
            if result is None:
                break

            requests_page = result.get('results', [])
            if not requests_page:
                break

            all_requests.extend(requests_page)

            page_info = result.get('pageInfo', {})
            total = self._coerce_int(page_info.get('results'))
            if total is not None and len(all_requests) >= total:
                break

            if len(requests_page) < take:
                break

        return all_requests

    def _normalize_status_token(self, value: Any, status_map: Optional[Dict[int, str]] = None) -> Optional[str]:
        """Normalize status values to uppercase symbolic tokens."""
        if value is None:
            return None

        if isinstance(value, str):
            token = value.strip().upper()
            return token or None

        coerced_int = self._coerce_int(value)
        if coerced_int is None:
            return None

        if status_map and coerced_int in status_map:
            return status_map[coerced_int]

        return str(coerced_int)

    def _extract_status_tokens(self, request: Dict[str, Any]) -> Set[str]:
        """Extract request/media status tokens from a request payload."""
        tokens: Set[str] = set()

        request_status = self._normalize_status_token(
            request.get('status'),
            REQUEST_STATUS_MAP,
        )
        if request_status:
            tokens.add(request_status)

        request_status_text = self._normalize_status_token(
            request.get('statusText') or request.get('requestStatus')
        )
        if request_status_text:
            tokens.add(request_status_text)

        media = request.get('media', {}) if isinstance(request, dict) else {}
        media_status = self._normalize_status_token(
            media.get('status'),
            MEDIA_STATUS_MAP,
        )
        if media_status:
            tokens.add(media_status)

        media_status_text = self._normalize_status_token(media.get('statusText'))
        if media_status_text:
            tokens.add(media_status_text)

        if media.get('isAvailable') is True:
            tokens.add('AVAILABLE')

        return tokens

    def get_user_requests(
        self,
        user_id: int,
        statuses: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get Seerr requests for a specific user with optional status filtering.

        Args:
            user_id: Seerr user ID
            statuses: Optional status tokens to include. Example:
                ['APPROVED', 'PROCESSING', 'AVAILABLE']

        Returns:
            List of matching request dictionaries
        """
        target_user_id = self._coerce_int(user_id)
        if target_user_id is None:
            return []

        status_filter = {
            str(status).strip().upper()
            for status in (statuses or [])
            if str(status).strip()
        }

        user_requests: List[Dict[str, Any]] = []

        for request in self.get_requests():
            requested_by = request.get('requestedBy', {}) if isinstance(request, dict) else {}
            request_user_id = self._coerce_int(
                requested_by.get('id')
                or request.get('requestedById')
                or request.get('requestedBy_userId')
                or request.get('userId')
            )

            if request_user_id != target_user_id:
                continue

            if status_filter:
                status_tokens = self._extract_status_tokens(request)
                if not status_tokens.intersection(status_filter):
                    continue

            user_requests.append(request)

        return user_requests

    def get_completed_requests(self, user_id: int) -> List[Dict[str, Any]]:
        """Get requests in completion-oriented states for a specific user."""
        return self.get_user_requests(
            user_id=user_id,
            statuses=['APPROVED', 'PROCESSING', 'AVAILABLE', 'FILLED'],
        )

    def find_existing_request(self, media_type: str, media_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Find an existing Seerr request for a specific user and media item.

        Args:
            media_type: 'movie' or 'tv'
            media_id: TMDB media ID
            user_id: Seerr user ID

        Returns:
            Matching request dict, or None if not found
        """
        normalized_media_type = 'tv' if str(media_type).lower() == 'tv' else 'movie'
        target_media_id = self._coerce_int(media_id)
        target_user_id = self._coerce_int(user_id)

        if target_media_id is None or target_user_id is None:
            return None

        for request in self.get_requests():
            media = request.get('media', {}) if isinstance(request, dict) else {}
            request_media_type = str(
                media.get('mediaType')
                or request.get('mediaType')
                or request.get('type')
                or ''
            ).lower()

            request_media_id = self._coerce_int(
                media.get('tmdbId')
                or request.get('mediaId')
            )

            requested_by = request.get('requestedBy', {}) if isinstance(request, dict) else {}
            request_user_id = self._coerce_int(
                requested_by.get('id')
                or request.get('requestedById')
                or request.get('userId')
            )

            if (
                request_media_type == normalized_media_type
                and request_media_id == target_media_id
                and request_user_id == target_user_id
            ):
                return request

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
        all_users = []
        page = 1
        
        while True:
            result = self._make_request('GET', f'/user?take=100&skip={(page-1)*100}')
            if result is None:
                break
            
            users = result.get('results', [])
            if not users:
                break
            
            all_users.extend(users)
            
            # Check if we've fetched all users
            total = result.get('pageInfo', {}).get('results', 0)
            if len(all_users) >= total:
                break
            
            page += 1
            
            # Safety limit
            if page > 10:
                logger.warning("Reached pagination safety limit for Seerr users")
                break
        
        logger.debug(f"Fetched {len(all_users)} Seerr users")
        return all_users

    def get_request(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Get request details.
        
        Args:
            request_id: Request ID
            
        Returns:
            Request data if found, None otherwise
        """
        return self._make_request('GET', f'/request/{request_id}')
    
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
