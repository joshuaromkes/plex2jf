"""Plex API client."""
import logging
from typing import List, Optional, Dict, Any

from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import PlexApiException

logger = logging.getLogger(__name__)


class PlexWatchlistItem:
    """Represents a Plex watchlist item."""
    
    def __init__(self, plex_item: Any, username: str, user_id: Optional[str] = None):
        self.plex_item = plex_item
        self.username = username
        self.user_id = user_id
        self.title = plex_item.title
        self.type = plex_item.type  # 'movie' or 'show'
        
        # Extract external IDs from GUIDs
        self.tmdb_id: Optional[str] = None
        self.imdb_id: Optional[str] = None
        self.tvdb_id: Optional[str] = None
        
        if hasattr(plex_item, 'guids'):
            for guid in plex_item.guids:
                guid_str = str(guid.id) if hasattr(guid, 'id') else str(guid)
                if 'tmdb://' in guid_str:
                    self.tmdb_id = guid_str.split('tmdb://')[1]
                elif 'imdb://' in guid_str:
                    self.imdb_id = guid_str.split('imdb://')[1]
                elif 'tvdb://' in guid_str:
                    self.tvdb_id = guid_str.split('tvdb://')[1]
    
    def __repr__(self) -> str:
        return f"<PlexWatchlistItem {self.title} ({self.type})>"


class PlexClient:
    """Client for interacting with Plex API."""
    
    def __init__(self, token: str, url: str = "https://plex.tv"):
        self.token = token
        self.url = url
        self._account: Optional[MyPlexAccount] = None
    
    def connect(self) -> None:
        """Connect to Plex account."""
        try:
            self._account = MyPlexAccount(token=self.token)
            logger.info(f"Connected to Plex account: {self._account.username}")
        except PlexApiException as e:
            logger.error(f"Failed to connect to Plex: {e}")
            raise
    
    def get_managed_users(self) -> List[Dict[str, Any]]:
        """Get list of managed/home users.
        
        Returns:
            List of user dictionaries with 'id', 'title', 'uuid' keys
        """
        if self._account is None:
            self.connect()
        
        users = []
        try:
            for user in self._account.users():
                users.append({
                    'id': user.id,
                    'title': user.title,
                    'uuid': user.uuid if hasattr(user, 'uuid') else None,
                })
            logger.info(f"Found {len(users)} managed users")
        except PlexApiException as e:
            logger.error(f"Failed to get managed users: {e}")
        
        return users
    
    def get_watchlist(self, username: Optional[str] = None) -> List[PlexWatchlistItem]:
        """Get watchlist for a specific user or all managed users.
        
        Args:
            username: Specific username to fetch watchlist for. If None, fetches for all users.
            
        Returns:
            List of watchlist items
        """
        if self._account is None:
            self.connect()
        
        items = []
        
        try:
            if username:
                # Get watchlist for specific user
                user_account = self._account.user(username)
                watchlist = user_account.watchlist()
                user_id = self._get_user_id(username)
                
                for item in watchlist:
                    items.append(PlexWatchlistItem(item, username, user_id))
            else:
                # Get watchlist for all managed users
                for user in self._account.users():
                    try:
                        user_account = self._account.user(user.title)
                        watchlist = user_account.watchlist()
                        user_id = user.id if hasattr(user, 'id') else None
                        
                        for item in watchlist:
                            items.append(PlexWatchlistItem(item, user.title, user_id))
                        
                        logger.debug(f"Found {len(watchlist)} items in {user.title}'s watchlist")
                    except Exception as e:
                        logger.warning(f"Failed to get watchlist for {user.title}: {e}")
            
            logger.info(f"Total watchlist items: {len(items)}")
            
        except PlexApiException as e:
            logger.error(f"Failed to get watchlist: {e}")
        
        return items
    
    def _get_user_id(self, username: str) -> Optional[str]:
        """Get user ID for a username."""
        try:
            for user in self._account.users():
                if user.title == username:
                    return user.id if hasattr(user, 'id') else None
        except Exception:
            pass
        return None
    
    def health_check(self) -> bool:
        """Check if Plex connection is healthy."""
        try:
            if self._account is None:
                self.connect()
            # Try to fetch account info as health check
            _ = self._account.username
            return True
        except Exception as e:
            logger.error(f"Plex health check failed: {e}")
            return False