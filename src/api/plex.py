"""Plex API client."""
import json
import logging
import requests
from typing import List, Optional, Dict, Any

from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import PlexApiException

logger = logging.getLogger(__name__)

# Plex API endpoints
DISCOVER_API = "https://discover.provider.plex.tv"
COMMUNITY_API = "https://community.plex.tv/api"


class PlexGraphQLUserNotFoundError(Exception):
    """Raised when Plex GraphQL cannot resolve a user for a provided ID."""


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
    
    def get_watchlist(self, username: Optional[str] = None, mapped_usernames: List[str] = None) -> List[PlexWatchlistItem]:
        """Get watchlist using GraphQL API (primary method).
        
        Uses the Plex GraphQL API at community.plex.tv/api.
        Can fetch watchlists for self and mapped friends.
        
        Args:
            username: Specific username to fetch watchlist for. If None, fetches for all mapped users.
            mapped_usernames: List of mapped usernames to filter by (only fetch watchlists for these users)
            
        Returns:
            List of watchlist items
        """
        items = []
        
        try:
            # First, get the account info to know the username
            if self._account is None:
                self.connect()
            
            account_username = self._account.username
            account_user_id = str(self._account.id)
            
            logger.info(f"Fetching watchlist for {account_username} using GraphQL API")
            
            # Try with multiple methods in sequence until one succeeds
            try:
                # Try new GraphQL API first (watchlistarr-style)
                items = self._get_watchlist_graphql_watchlistarr(account_username, account_user_id, mapped_usernames)
                if items:
                    logger.info(f"GraphQL API returned {len(items)} items")
                else:
                    logger.warning("GraphQL API returned empty watchlist, trying PlexAPI fallback")
                    
                    # Fall back to PlexAPI if GraphQL returns nothing
                    try:
                        items = self._get_watchlist_plexapi(account_username, account_user_id)
                    except Exception as plex_error:
                        logger.error(f"PlexAPI library watchlist() failed: {plex_error}")
                        # Try direct API as final fallback
                        logger.info("Trying direct API call as final fallback")
                        items = self._get_watchlist_direct_api(account_username, account_user_id)
                        
            except Exception as e:
                logger.error(f"GraphQL API failed: {e}")
                
                # Try PlexAPI as fallback
                try:
                    items = self._get_watchlist_plexapi(account_username, account_user_id)
                except Exception as plex_error:
                    logger.error(f"PlexAPI fallback also failed: {plex_error}")
                    # Try direct API as final fallback
                    items = self._get_watchlist_direct_api(account_username, account_user_id)
            
            logger.info(f"Total watchlist items: {len(items)}")
            
        except Exception as e:
            logger.error(f"Failed to get watchlist: {e}")
        
        return items
    
    def _get_watchlist_graphql(self, account_username: str, account_user_id: str, user_uuid: str = None) -> List[PlexWatchlistItem]:
        """Get watchlist using Plex GraphQL API.
        
        This method uses the community.plex.tv GraphQL API which can fetch
        watchlists with just the admin token.
        
        Modified based on watchlistarr's implementation.
        """
        items = []
        
        # Use numeric ID (the API might not accept UUID)
        query_user_id = account_user_id
        
        # Query to get watchlist using the GraphQL API
        query = """
        query GetWatchlist {
            me {
                id
                username
                watchlist {
                    edges {
                        node {
                            id
                            title
                            type
                            ratingKey
                            guid
                            year
                        }
                    }
                }
                friends {
                    edges {
                        node {
                            id
                            username
                        }
                    }
                }
            }
        }
        """
        
        headers = {
            'Content-Type': 'application/json',
            'X-Plex-Token': self.token
        }
        
        # No variables needed for me query
        payload = {
            'query': query
        }
        
        # Variables section is not needed for this query
        # This was causing the error: name 'variables' is not defined
        
        logger.info(f"Making GraphQL request to {COMMUNITY_API}")
        
        try:
            response = requests.post(
                COMMUNITY_API,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            logger.info(f"GraphQL response status: {response.status_code}")
            
            if response.status_code == 200:
                # Log a sample of the response to help debug
                logger.debug(f"GraphQL response preview: {response.text[:200]}")
                
                try:
                    data = response.json()
                    
                    # Check for GraphQL errors
                    if 'errors' in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        return items
                    
                    # Parse the response - using 'me' query
                    user_data = data.get('data', {}).get('me')
                    if not user_data:
                        logger.warning("No user data in GraphQL response")
                        logger.debug(f"Response data: {data}")
                        return items
                    
                    # Process the admin user's watchlist
                    watchlist = user_data.get('watchlist', {})
                    if not watchlist:
                        logger.warning("No watchlist found in GraphQL response")
                        return items
                        
                    watchlist_edges = watchlist.get('edges', [])
                    logger.info(f"Found {len(watchlist_edges)} items in watchlist")
                except Exception as json_err:
                    logger.error(f"Error parsing GraphQL response JSON: {json_err}")
                    return items
                
                for edge in watchlist_edges:
                    node = edge.get('node', {})
                    
                    # Extract title and type
                    title = node.get('title', 'Unknown')
                    item_type = node.get('type', 'movie')
                    guid = node.get('guid', '')
                    rating_key = node.get('ratingKey', '')

                    # Diagnostic logging: capture raw GraphQL type and current mapping behavior
                    mapped_type_preview = 'movie' if item_type == 'movie' else 'show'
                    logger.info(
                        "GraphQL watchlist type mapping (admin): title=%s raw_type=%s mapped_type=%s",
                        title,
                        item_type,
                        mapped_type_preview,
                    )
                    
                    # Normalize type - Plex GraphQL returns MOVIE/SHOW in uppercase
                    normalized_type = 'movie' if item_type.lower() == 'movie' else 'show'
                    
                    # Create a simple object to hold the item data
                    item_obj = type('PlexItem', (), {
                        'title': title,
                        'type': normalized_type,
                        'guids': [guid] if guid else []
                    })()
                    
                    items.append(PlexWatchlistItem(item_obj, account_username, account_user_id))
                
                logger.info(f"Total items from GraphQL: {len(items)}")
                
            else:
                logger.warning(f"GraphQL request failed with status {response.status_code}")
                logger.warning(f"GraphQL response: {response.text[:1000]}")
                
        except requests.RequestException as e:
            logger.error(f"GraphQL request failed: {e}")
        except Exception as e:
            logger.error(f"Error parsing GraphQL response: {e}")
        
        return items
    
    def _get_watchlist_graphql_watchlistarr(self, account_username: str, account_user_id: str, mapped_usernames: List[str] = None) -> List[PlexWatchlistItem]:
        """Get watchlist using Plex GraphQL API - watchlistarr implementation.
        
        This uses the correct GraphQL query structure from watchlistarr:
        1. Get all friends using allFriendsV2 query
        2. For each mapped friend, get their watchlist using user(id: $uuid) query
        
        Args:
            account_username: The Plex account username
            account_user_id: The Plex account user ID
            mapped_usernames: Optional list of usernames to filter (only fetch watchlists for these users)
        
        Returns:
            List of watchlist items from mapped friends
        """
        items = []
        
        try:
            # Step 1: Get all friends
            friends = self._get_friends_graphql()
            
            # Always include self - need to get UUID for the account user
            account_uuid = self._get_user_uuid()
            if not account_uuid:
                # Fallback: try to find self in friends list
                for friend in friends or []:
                    if friend.get('username') == account_username:
                        account_uuid = friend.get('id')
                        break
                # Last resort: use numeric ID (will likely fail but let's try)
                if not account_uuid:
                    account_uuid = account_user_id
                    logger.warning(f"Could not get UUID for account, using numeric ID: {account_user_id}")
            
            # Normalize mapped usernames for comparison (lowercase, remove spaces)
            normalized_mapped = {}
            if mapped_usernames:
                normalized_mapped = {u.lower().replace(' ', ''): u for u in mapped_usernames}
                logger.info(f"Normalized mapped usernames: {list(normalized_mapped.keys())}")

            # Collect candidate users from all known sources:
            # 1) account owner
            # 2) Plex friends (allFriendsV2)
            # 3) managed/home users (self._account.users())
            # This ensures mapped users that are not returned by allFriendsV2 are still fetched.
            users_by_normalized: Dict[str, Dict[str, Any]] = {}

            def _add_candidate(user_id: Optional[str], username: Optional[str]) -> None:
                if not user_id or not username:
                    return
                normalized = username.lower().replace(' ', '')
                user_id_str = str(user_id)

                if normalized not in users_by_normalized:
                    users_by_normalized[normalized] = {
                        'username': username,
                        'id_candidates': [user_id_str],
                    }
                    return

                # Keep the first discovered display name but extend candidate IDs.
                existing = users_by_normalized[normalized]
                existing_candidates = existing.setdefault('id_candidates', [])
                if user_id_str not in existing_candidates:
                    existing_candidates.append(user_id_str)

            # Account owner candidate
            _add_candidate(account_uuid, account_username)
            # Add numeric account ID as fallback if UUID resolution is wrong/absent.
            if str(account_user_id) != str(account_uuid):
                _add_candidate(account_user_id, account_username)

            # Friend candidates
            if friends:
                logger.info(f"Found {len(friends)} friends, collecting candidates")
                for friend in friends:
                    _add_candidate(friend.get('id'), friend.get('username'))

            # Managed/home user candidates
            managed_users = self.get_managed_users()
            if managed_users:
                logger.info(f"Found {len(managed_users)} managed users, collecting candidates")
                for managed_user in managed_users:
                    managed_uuid = managed_user.get('uuid')
                    managed_numeric_id = managed_user.get('id')
                    managed_username = managed_user.get('title')
                    # Try both UUID and numeric ID for managed users since some Plex
                    # responses expose IDs inconsistently for GraphQL lookup.
                    _add_candidate(managed_uuid, managed_username)
                    if str(managed_numeric_id) != str(managed_uuid):
                        _add_candidate(managed_numeric_id, managed_username)

            users_to_fetch = []
            if normalized_mapped:
                for normalized_username, original_username in normalized_mapped.items():
                    candidate = users_by_normalized.get(normalized_username)
                    if candidate:
                        users_to_fetch.append(candidate)
                        logger.info(
                            "Adding mapped user: %s (matched to %s)",
                            candidate.get('username'),
                            original_username,
                        )
                    else:
                        logger.warning(
                            "Mapped Plex user not found in account/friends/managed users: %s",
                            original_username,
                        )
            else:
                # If no mapped users specified, fetch all discovered candidates.
                users_to_fetch = list(users_by_normalized.values())

            if not users_to_fetch:
                logger.warning("No users resolved for watchlist fetch after mapping/candidate filtering")
                return items
            
            user_names = [u.get('username', 'Unknown') for u in users_to_fetch]
            logger.info(f"Fetching watchlists for {len(users_to_fetch)} users: {user_names}")
            
            # Step 2: Get watchlist for each user
            for user in users_to_fetch:
                username = user.get('username', 'Unknown')
                id_candidates = user.get('id_candidates') or []

                if not id_candidates:
                    logger.warning("No user ID candidates available for %s", username)
                    continue

                fetched = False
                last_error: Optional[Exception] = None

                for user_id in id_candidates:
                    try:
                        user_items = self._get_watchlist_for_user_graphql(username, user_id)
                        items.extend(user_items)
                        logger.info(f"Found {len(user_items)} items in watchlist for {username}")
                        if len(id_candidates) > 1:
                            logger.info("Resolved %s using GraphQL user ID candidate: %s", username, user_id)
                        fetched = True
                        break
                    except PlexGraphQLUserNotFoundError as e:
                        last_error = e
                        logger.warning(
                            "GraphQL user lookup failed for %s with ID candidate %s; trying next candidate",
                            username,
                            user_id,
                        )
                        continue
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Failed to get watchlist for {username}: {e}")
                        break

                if not fetched and last_error:
                    logger.warning(
                        "Could not fetch watchlist for %s after trying %d ID candidate(s): %s",
                        username,
                        len(id_candidates),
                        last_error,
                    )
            
        except Exception as e:
            logger.error(f"GraphQL watchlistarr-style implementation failed: {e}")
        
        return items
    
    def _get_friends_graphql(self) -> List[Dict[str, Any]]:
        """Get all friends using Plex GraphQL API.
        
        Based on watchlistarr's GetAllFriends query.
        
        Returns:
            List of friend dictionaries with 'id' and 'username' keys
        """
        friends = []
        
        query = """
        query GetAllFriends {
          allFriendsV2 {
            user {
              id
              username
            }
          }
        }
        """
        
        headers = {
            'Content-Type': 'application/json',
            'X-Plex-Token': self.token,
            'Accept': 'application/json'
        }
        
        payload = {
            'query': query,
            'variables': {}  # No variables needed for this query
        }
        
        logger.info(f"Fetching friends from Plex GraphQL API")
        
        try:
            response = requests.post(
                COMMUNITY_API,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            logger.info(f"Friends query response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for GraphQL errors
                if 'errors' in data:
                    logger.error(f"GraphQL errors in friends query: {data['errors']}")
                    return friends
                
                # Parse the response
                all_friends = data.get('data', {}).get('allFriendsV2', [])
                
                for friend_data in all_friends:
                    user = friend_data.get('user', {})
                    if user and user.get('id'):
                        friends.append({
                            'id': user.get('id'),
                            'username': user.get('username', 'Unknown')
                        })
                
                logger.info(f"Successfully fetched {len(friends)} friends")
            else:
                logger.warning(f"Failed to fetch friends: HTTP {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")
                
        except Exception as e:
            logger.error(f"Error fetching friends: {e}")
        
        return friends
    
    def _get_watchlist_for_user_graphql(self, username: str, user_id: str, page: Optional[str] = None) -> List[PlexWatchlistItem]:
        """Get watchlist for a specific user using Plex GraphQL API.
        
        Based on watchlistarr's GetWatchlistHub query with pagination support.
        
        Args:
            username: The username to fetch watchlist for
            user_id: The user ID (UUID) to fetch watchlist for
            page: Optional pagination cursor for fetching next page
            
        Returns:
            List of watchlist items
        """
        items = []
        
        query = """
        query GetWatchlistHub($uuid: ID = "", $first: PaginationInt!, $after: String) {
          user(id: $uuid) {
            watchlist(first: $first, after: $after) {
              nodes {
                id
                title
                type
                key
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """
        
        # Build variables
        variables = {
            "first": 100,  # Get 100 items at a time
            "uuid": user_id
        }
        
        if page:
            variables["after"] = page
        
        headers = {
            'Content-Type': 'application/json',
            'X-Plex-Token': self.token,
            'Accept': 'application/json'
        }
        
        payload = {
            'query': query,
            'variables': variables
        }
        
        logger.debug(f"Fetching watchlist for user {username} (page: {page or 'first'})")
        
        try:
            response = requests.post(
                COMMUNITY_API,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            logger.debug(f"Watchlist query response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for GraphQL errors
                if 'errors' in data:
                    errors = data['errors']
                    logger.error(f"GraphQL errors in watchlist query for {username}: {errors}")

                    error_messages = " | ".join(
                        str(err.get('message', err)) if isinstance(err, dict) else str(err)
                        for err in errors
                    )
                    if (
                        "User not found" in error_messages
                        or "Data loader item not found: users uuid" in error_messages
                    ):
                        raise PlexGraphQLUserNotFoundError(
                            f"GraphQL could not resolve user '{username}' with id '{user_id}'"
                        )
                    return items
                
                # Parse the response
                user_data = data.get('data', {}).get('user', {})
                watchlist_data = user_data.get('watchlist', {})
                nodes = watchlist_data.get('nodes', [])
                page_info = watchlist_data.get('pageInfo', {})
                
                # Process watchlist items
                for node in nodes:
                    title = node.get('title', 'Unknown')
                    item_type = node.get('type', 'movie')
                    key = node.get('key', '')

                    # Diagnostic logging: capture raw GraphQL type and current mapping behavior
                    mapped_type_preview = 'movie' if item_type == 'movie' else 'show'
                    logger.info(
                        "GraphQL watchlist type mapping (friend): title=%s raw_type=%s mapped_type=%s",
                        title,
                        item_type,
                        mapped_type_preview,
                    )
                    
                    # Fetch external IDs using the key
                    external_ids = self._fetch_item_metadata(key) if key else {}
                    
                    # Normalize type - Plex GraphQL returns MOVIE/SHOW in uppercase
                    normalized_type = 'movie' if item_type.lower() == 'movie' else 'show'
                    
                    # Create a simple object to hold the item data
                    item_obj = type('PlexItem', (), {
                        'title': title,
                        'type': normalized_type,
                        'guids': external_ids.get('guids', [])
                    })()
                    
                    # Create PlexWatchlistItem with external IDs
                    watchlist_item = PlexWatchlistItem(item_obj, username, user_id)
                    # Set the external IDs directly
                    watchlist_item.tmdb_id = external_ids.get('tmdb_id')
                    watchlist_item.imdb_id = external_ids.get('imdb_id')
                    watchlist_item.tvdb_id = external_ids.get('tvdb_id')
                    
                    items.append(watchlist_item)
                
                # Handle pagination
                has_next_page = page_info.get('hasNextPage', False)
                end_cursor = page_info.get('endCursor')
                
                if has_next_page and end_cursor:
                    logger.debug(f"Fetching next page for {username} with cursor {end_cursor}")
                    next_page_items = self._get_watchlist_for_user_graphql(username, user_id, end_cursor)
                    items.extend(next_page_items)
                
            else:
                logger.warning(f"Failed to fetch watchlist for {username}: HTTP {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")
                
        except Exception as e:
            logger.error(f"Error fetching watchlist for {username}: {e}")
        
        return items
    
    def _fetch_item_metadata(self, key: str) -> Dict[str, Any]:
        """Fetch item metadata to get external IDs (TMDB, IMDB, TVDB).
        
        Based on watchlistarr's approach of making a follow-up API call
        to get full metadata including GUIDs.
        
        Args:
            key: The item key from GraphQL (e.g., "/library/metadata/12345")
            
        Returns:
            Dictionary with 'guids', 'tmdb_id', 'imdb_id', 'tvdb_id'
        """
        result = {
            'guids': [],
            'tmdb_id': None,
            'imdb_id': None,
            'tvdb_id': None
        }
        
        if not key:
            return result
        
        # Clean the key (remove /children suffix if present)
        if key.endswith('/children'):
            key = key[:-9]
        
        # Build URL
        url = f"{DISCOVER_API}{key}"
        
        headers = {
            'X-Plex-Token': self.token,
            'Accept': 'application/json'
        }
        
        try:
            logger.info(f"Fetching metadata for key: {key}")
            response = requests.get(url, headers=headers, timeout=30)
            
            logger.info(f"Metadata API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.debug(f"Metadata response keys: {list(data.keys())}")
                    
                    # Extract metadata from response
                    metadata = None
                    if isinstance(data, dict):
                        if 'Metadata' in data:
                            metadata = data['Metadata']
                            logger.debug(f"Found Metadata in root")
                        elif 'MediaContainer' in data and 'Metadata' in data['MediaContainer']:
                            metadata = data['MediaContainer']['Metadata']
                            logger.debug(f"Found Metadata in MediaContainer")
                    
                    if metadata and isinstance(metadata, list) and len(metadata) > 0:
                        item = metadata[0]
                        logger.debug(f"Processing metadata for item: {item.get('title', 'Unknown')}")
                        
                        # Extract GUIDs
                        if 'Guid' in item and isinstance(item['Guid'], list):
                            guids = []
                            for guid in item['Guid']:
                                if isinstance(guid, dict) and 'id' in guid:
                                    guid_str = guid['id']
                                    guids.append(guid_str)
                                    
                                    # Parse external IDs
                                    if 'tmdb://' in guid_str:
                                        result['tmdb_id'] = guid_str.split('tmdb://')[1]
                                        logger.info(f"Found TMDB ID for {item.get('title', 'Unknown')}: {result['tmdb_id']}")
                                    elif 'imdb://' in guid_str:
                                        result['imdb_id'] = guid_str.split('imdb://')[1]
                                    elif 'tvdb://' in guid_str:
                                        result['tvdb_id'] = guid_str.split('tvdb://')[1]
                            
                            result['guids'] = guids
                            logger.debug(f"Found {len(guids)} GUIDs for {item.get('title', 'Unknown')}")
                        else:
                            logger.warning(f"No GUIDs found in metadata for {item.get('title', 'Unknown')}")
                    else:
                        logger.warning(f"No metadata found for key: {key}")
                            
                except ValueError:
                    # Response is not JSON (might be XML)
                    logger.debug(f"Metadata response for {key} is not JSON")
            else:
                logger.debug(f"Failed to fetch metadata for {key}: HTTP {response.status_code}")
                
        except Exception as e:
            logger.debug(f"Error fetching metadata for {key}: {e}")
        
        return result
    
    def _get_watchlist_plexapi(self, account_username: str, account_user_id: str) -> List[PlexWatchlistItem]:
        """Get watchlist using PlexAPI library as fallback."""
        items = []
        
        try:
            watchlist = self._account.watchlist()
            logger.info(f"PlexAPI watchlist() returned {len(watchlist)} items")
            
            for item in watchlist:
                items.append(PlexWatchlistItem(item, account_username, account_user_id))
            
            logger.info(f"Found {len(watchlist)} items in watchlist for {account_username}")
        except Exception as e:
            logger.error(f"PlexAPI library watchlist() failed: {e}")
            # Try direct API as fallback
            logger.info("Trying direct API call as fallback")
            items = self._get_watchlist_direct_api(account_username, account_user_id)
        
        return items
    
    def _get_watchlist_direct_api(self, account_username: str, account_user_id: str) -> List[PlexWatchlistItem]:
        """Get watchlist using direct API calls as fallback.
        
        First tries the Discover API style used by Overseerr,
        then attempts alternative endpoints if the first one fails.
        """
        items = []
        
        # Check multiple possible API endpoints
        endpoints = [
            # Regular discover API (Overseerr style)
            {
                "url": f"{DISCOVER_API}/library/sections/watchlist/all",
                "params": {
                    "X-Plex-Token": self.token,
                    "includeFields": "title,type,year,ratingKey",
                    "includeElements": "Guid",
                    "sort": "watchlistedAt:desc",
                    "includeCollections": "1",
                    "includeExternalMedia": "1"
                }
            },
            # Alternative endpoint
            {
                "url": f"{DISCOVER_API}/library/sections/watchlist",
                "params": {
                    "X-Plex-Token": self.token
                }
            },
            # Try metadata API as another alternative
            {
                "url": "https://metadata.provider.plex.tv/library/sections/watchlist/all",
                "params": {
                    "X-Plex-Token": self.token
                }
            }
        ]
        
        # Try each endpoint until one works
        for endpoint in endpoints:
            base_url = endpoint["url"]
            params = endpoint["params"]
            
            logger.info(f"Trying direct API call to: {base_url}")
            
            try:
                response = requests.get(base_url, params=params, timeout=30)
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Check if response is empty before trying to parse
                    if not response.text.strip():
                        logger.warning(f"Received empty response body from {base_url}")
                        continue  # Try next endpoint
                    
                    # Log first 100 chars of response for debugging
                    logger.debug(f"Response preview: {response.text[:100]}")
                    
                    try:
                        # Try to parse as JSON
                        data = response.json()
                        
                        if isinstance(data, dict):
                            logger.debug(f"Response data keys: {list(data.keys())}")
                            
                            # Extract metadata based on response structure
                            metadata = []
                            if "Metadata" in data:
                                metadata = data.get("Metadata", [])
                            elif "MediaContainer" in data:
                                # Alternative structure
                                metadata = data.get("MediaContainer", {}).get("Metadata", [])
                            
                            if metadata:
                                for item in metadata:
                                    # Extract GUIDs from Guid array
                                    guids = []
                                    if 'Guid' in item and isinstance(item['Guid'], list):
                                        for guid in item['Guid']:
                                            if isinstance(guid, dict) and 'id' in guid:
                                                guids.append(guid['id'])
                                    
                                    # Create a simple object to hold the item data
                                    item_obj = type('PlexItem', (), {
                                        'title': item.get('title', 'Unknown'),
                                        'type': 'movie' if item.get('type') == 'movie' else 'show',
                                        'guids': guids
                                    })()
                                    
                                    items.append(PlexWatchlistItem(item_obj, account_username, account_user_id))
                                
                                logger.info(f"Found {len(metadata)} items using API at {base_url}")
                                return items  # Success - return items and stop trying other endpoints
                            else:
                                logger.warning(f"API at {base_url} returned empty metadata")
                        else:
                            logger.warning(f"API at {base_url} returned non-dict data: {type(data)}")
                    except ValueError as json_error:
                        # Failed to parse as JSON
                        logger.warning(f"Failed to parse JSON from {base_url}: {json_error}")
                        
                        # If it looks like XML, log that info
                        if "<?xml" in response.text[:100]:
                            logger.info(f"Response from {base_url} appears to be XML, not JSON")
                elif response.status_code == 404:
                    logger.debug(f"Endpoint not found: {base_url}")
                else:
                    logger.warning(f"Failed API call to {base_url}: HTTP {response.status_code}")
                    if response.text:
                        logger.debug(f"Error response: {response.text[:500]}")
            except Exception as e:
                logger.warning(f"Request to {base_url} failed: {str(e)}")
        
        # If we get here, all endpoints failed
        logger.warning("All API endpoints failed to return watchlist data")
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
    
    def _get_user_uuid(self) -> Optional[str]:
        """Get the current user's UUID for GraphQL API.
        
        The GraphQL API may require a UUID instead of numeric ID.
        """
        try:
            # Try to get the UUID from the account
            if hasattr(self._account, 'uuid'):
                return self._account.uuid
            
            # Try to get it from the user resource
            headers = {'X-Plex-Token': self.token}
            response = requests.get(
                "https://plex.tv/users/account",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('user', {}).get('uuid')
        except Exception as e:
            logger.warning(f"Failed to get user UUID: {e}")
        
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

    def test_connection(self) -> None:
        """Test connection to Plex. Raises exception if failed."""
        if self._account is None:
            self.connect()
        # Verify connection by accessing account info
        _ = self._account.username

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all Plex users including managed users.
        
        Returns:
            List of user dictionaries with 'id', 'username', 'email' keys
        """
        if self._account is None:
            self.connect()
        
        users = []
        
        # Add the main account owner
        try:
            users.append({
                'id': self._account.id,
                'username': self._account.username,
                'email': self._account.email if hasattr(self._account, 'email') else None,
            })
        except Exception as e:
            logger.warning(f"Failed to get account owner info: {e}")
        
        # Add managed/home users
        for user in self._account.users():
            try:
                users.append({
                    'id': user.id,
                    'username': user.title,
                    'email': user.email if hasattr(user, 'email') else None,
                })
            except Exception as e:
                logger.warning(f"Failed to get user info for {user}: {e}")
        
        return users
