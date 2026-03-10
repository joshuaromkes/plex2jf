"""Plex API client with watchlist support."""

import logging
from typing import Optional, List
import requests

from ..models.media_item import MediaItem, MediaType

logger = logging.getLogger(__name__)


class PlexClient:
    """Client for interacting with Plex Media Server."""
    
    PLEX_TV_URL = "https://discover.provider.plex.tv"
    
    def __init__(self, base_url: str, token: str):
        """Initialize Plex client.
        
        Args:
            base_url: Plex server URL (e.g., http://localhost:32400)
            token: Plex token (X-Plex-Token)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'X-Plex-Token': token,
            'Accept': 'application/json',
            'X-Plex-Client-Identifier': 'plex2jf-sync',
            'X-Plex-Product': 'Plex2JF',
            'X-Plex-Version': '0.1.0'
        })
    
    def _get(self, endpoint: str, params: Optional[dict] = None, use_tv: bool = False) -> dict:
        """Make a GET request to Plex API."""
        base = self.PLEX_TV_URL if use_tv else self.base_url
        url = f"{base}{endpoint}"
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def _post_graphql(self, query: str, variables: Optional[dict] = None) -> dict:
        """Make a GraphQL request to Plex TV."""
        url = f"{self.PLEX_TV_URL}/graphql"
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_account_info(self) -> dict:
        """Get Plex account information."""
        response = self.session.get("https://plex.tv/users/account.json", timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_users(self) -> List[dict]:
        """Get all users from the Plex server."""
        try:
            data = self._get("/api/users")
            return data.get('MediaContainer', {}).get('User', [])
        except Exception as e:
            logger.error(f"Failed to get Plex users: {e}")
            return []
    
    def get_watchlist(self, username: Optional[str] = None) -> List[MediaItem]:
        """Get watchlist for a user using GraphQL.
        
        This is the reliable method for accessing Plex watchlists programmatically.
        The watchlist is associated with the Plex account, not the server.
        
        Args:
            username: Plex username to get watchlist for. If None, uses the token's account.
            
        Returns:
            List of MediaItem objects on the watchlist
        """
        logger.debug(f"Fetching watchlist for user: {username or 'token owner'}")
        
        # GraphQL query for watchlist
        query = """
        query GetWatchlist($first: Int!, $after: String) {
            user {
                watchlist(first: $first, after: $after) {
                    nodes {
                        id
                        title
                        type
                        year
                        ratingKey
                        key
                        thumb
                        art
                        guid
                        slug
                        summary
                        tagline
                        duration
                        rating
                        audienceRating
                        contentRating
                        originallyAvailableAt
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
        """
        
        variables = {
            "first": 100,
            "after": None
        }
        
        watchlist_items = []
        has_next = True
        
        try:
            while has_next:
                result = self._post_graphql(query, variables)
                
                if 'errors' in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                    break
                
                data = result.get('data', {}).get('user', {}).get('watchlist', {})
                nodes = data.get('nodes', [])
                page_info = data.get('pageInfo', {})
                
                for node in nodes:
                    try:
                        media_type = MediaType.MOVIE if node.get('type') == 'movie' else MediaType.TV_SHOW
                        
                        # Extract IDs from guid
                        tmdb_id = None
                        tvdb_id = None
                        imdb_id = None
                        
                        guid = node.get('guid', '')
                        if 'tmdb://' in guid:
                            tmdb_id = int(guid.split('tmdb://')[1].split('?')[0])
                        if 'tvdb://' in guid:
                            tvdb_id = int(guid.split('tvdb://')[1].split('?')[0])
                        if 'imdb://' in guid:
                            imdb_id = guid.split('imdb://')[1].split('?')[0]
                        
                        item = MediaItem(
                            title=node.get('title', 'Unknown'),
                            year=node.get('year'),
                            media_type=media_type,
                            tmdb_id=tmdb_id,
                            tvdb_id=tvdb_id,
                            imdb_id=imdb_id,
                            plex_rating_key=node.get('ratingKey')
                        )
                        watchlist_items.append(item)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse watchlist item: {e}")
                        continue
                
                has_next = page_info.get('hasNextPage', False)
                if has_next:
                    variables['after'] = page_info.get('endCursor')
                
                # Safety limit
                if len(watchlist_items) >= 1000:
                    logger.warning("Watchlist limit reached (1000 items)")
                    break
                    
        except Exception as e:
            logger.error(f"Failed to fetch watchlist: {e}")
        
        logger.info(f"Found {len(watchlist_items)} items in watchlist")
        return watchlist_items
    
    def get_library_items(self, section_id: int) -> List[dict]:
        """Get all items from a library section."""
        try:
            data = self._get(f"/library/sections/{section_id}/all")
            return data.get('MediaContainer', {}).get('Metadata', [])
        except Exception as e:
            logger.error(f"Failed to get library items: {e}")
            return []
    
    def get_libraries(self) -> List[dict]:
        """Get all library sections."""
        try:
            data = self._get("/library/sections")
            return data.get('MediaContainer', {}).get('Directory', [])
        except Exception as e:
            logger.error(f"Failed to get libraries: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check if Plex server is reachable."""
        try:
            response = self.session.get(f"{self.base_url}/identity", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Plex health check failed: {e}")
            return False
