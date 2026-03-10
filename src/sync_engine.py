"""Core sync engine for Plex2JF."""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Set

from .models.user_mapping import UserMapping, UserMappings
from .models.media_item import MediaItem
from .models.sync_state import SyncState, UserSyncState
from .api_clients.plex_client import PlexClient
from .api_clients.jellyfin_client import JellyfinClient
from .api_clients.seerr_client import SeerrClient

logger = logging.getLogger(__name__)


class SyncEngine:
    """Engine for synchronizing watchlists and requests between Plex, Jellyfin, and Seerr."""
    
    def __init__(
        self,
        plex_client: PlexClient,
        jellyfin_client: JellyfinClient,
        seerr_client: SeerrClient,
        user_mappings: UserMappings,
        state_file: Path
    ):
        """Initialize the sync engine.
        
        Args:
            plex_client: Plex API client
            jellyfin_client: Jellyfin API client
            seerr_client: Seerr API client
            user_mappings: User mappings configuration
            state_file: Path to store sync state
        """
        self.plex = plex_client
        self.jellyfin = jellyfin_client
        self.seerr = seerr_client
        self.user_mappings = user_mappings
        self.state_file = state_file
        self.state = SyncState.load(state_file)
        
        # Cache for user IDs
        self._jellyfin_user_ids: dict[str, str] = {}
        self._seerr_user_ids: dict[str, int] = {}
    
    def _get_jellyfin_user_id(self, username: str) -> str:
        """Get Jellyfin user ID, caching the result."""
        if username not in self._jellyfin_user_ids:
            user_id = self.jellyfin.get_user_id_by_name(username)
            if user_id:
                self._jellyfin_user_ids[username] = user_id
            else:
                raise ValueError(f"Jellyfin user not found: {username}")
        return self._jellyfin_user_ids[username]
    
    def _get_seerr_user_id(self, username: str) -> int:
        """Get Seerr user ID, caching the result."""
        if username not in self._seerr_user_ids:
            user_id = self.seerr.get_user_id_by_name(username)
            if user_id:
                self._seerr_user_ids[username] = user_id
            else:
                raise ValueError(f"Seerr user not found: {username}")
        return self._seerr_user_ids[username]
    
    def _populate_user_ids(self) -> None:
        """Populate user IDs for all mappings."""
        for mapping in self.user_mappings.mappings:
            try:
                jellyfin_id = self._get_jellyfin_user_id(mapping.jellyfin_username)
                mapping.jellyfin_user_id = jellyfin_id
                logger.debug(f"Found Jellyfin user ID for {mapping.jellyfin_username}: {jellyfin_id}")
            except ValueError as e:
                logger.warning(e)
            
            try:
                seerr_id = self._get_seerr_user_id(mapping.seerr_username)
                mapping.seerr_user_id = seerr_id
                logger.debug(f"Found Seerr user ID for {mapping.seerr_username}: {seerr_id}")
            except ValueError as e:
                logger.warning(e)
    
    def sync_plex_to_seerr(self, mapping: UserMapping) -> int:
        """Sync Plex watchlist to Seerr requests.
        
        Args:
            mapping: User mapping configuration
            
        Returns:
            Number of new requests created
        """
        if not mapping.seerr_user_id:
            logger.warning(f"No Seerr user ID for {mapping.plex_username}, skipping Plex->Seerr sync")
            return 0
        
        logger.info(f"Syncing Plex watchlist to Seerr for {mapping.plex_username}")
        
        # Get current watchlist
        current_watchlist = self.plex.get_watchlist(mapping.plex_username)
        current_keys = {item.unique_key for item in current_watchlist}
        
        # Get last known state
        user_state = self.state.get_user_state(mapping.plex_username)
        last_keys = user_state.last_plex_watchlist
        
        # Find new items
        new_keys = current_keys - last_keys
        new_items = [item for item in current_watchlist if item.unique_key in new_keys]
        
        logger.info(f"Found {len(new_items)} new items in Plex watchlist for {mapping.plex_username}")
        
        requests_created = 0
        for item in new_items:
            # Skip if already requested
            if self.seerr.request_exists(item, user_id=mapping.seerr_user_id):
                logger.debug(f"Request already exists for {item}")
                continue
            
            # Create request
            if self.seerr.create_request(item, mapping.seerr_user_id):
                requests_created += 1
                logger.info(f"Created Seerr request for {item}")
            else:
                logger.warning(f"Failed to create Seerr request for {item}")
        
        # Update state
        user_state.last_plex_watchlist = current_keys
        
        return requests_created
    
    def sync_plex_to_jellyfin(self, mapping: UserMapping) -> int:
        """Sync Plex watchlist to Jellyfin favorites.
        
        Args:
            mapping: User mapping configuration
            
        Returns:
            Number of new favorites created
        """
        if not mapping.jellyfin_user_id:
            logger.warning(f"No Jellyfin user ID for {mapping.plex_username}, skipping Plex->Jellyfin sync")
            return 0
        
        logger.info(f"Syncing Plex watchlist to Jellyfin for {mapping.plex_username}")
        
        # Get current watchlist
        current_watchlist = self.plex.get_watchlist(mapping.plex_username)
        current_keys = {item.unique_key for item in current_watchlist}
        
        # Get last known state
        user_state = self.state.get_user_state(mapping.plex_username)
        last_keys = user_state.last_plex_watchlist
        
        # Find new items (items added since last sync)
        # Note: We use the same state as Plex->Seerr, so we need to be careful
        # In a real implementation, you might want separate states
        new_keys = current_keys - last_keys
        new_items = [item for item in current_watchlist if item.unique_key in new_keys]
        
        favorites_created = 0
        for item in new_items:
            if self.jellyfin.favorite_media_item(mapping.jellyfin_user_id, item):
                favorites_created += 1
                logger.info(f"Favorited in Jellyfin: {item}")
            else:
                logger.warning(f"Failed to favorite in Jellyfin: {item}")
        
        return favorites_created
    
    def sync_seerr_to_jellyfin(self, mapping: UserMapping) -> int:
        """Sync Seerr requests to Jellyfin favorites.
        
        Args:
            mapping: User mapping configuration
            
        Returns:
            Number of new favorites created
        """
        if not mapping.jellyfin_user_id or not mapping.seerr_user_id:
            logger.warning(f"Missing user IDs for {mapping.plex_username}, skipping Seerr->Jellyfin sync")
            return 0
        
        logger.info(f"Syncing Seerr requests to Jellyfin for {mapping.seerr_username}")
        
        # Get current requests
        current_requests = self.seerr.get_pending_requests(user_id=mapping.seerr_user_id)
        
        # Also get approved/available requests
        try:
            approved = self.seerr.get_requests(user_id=mapping.seerr_user_id, status='approved')
            available = self.seerr.get_requests(user_id=mapping.seerr_user_id, status='available')
            current_requests.extend(self._requests_to_media_items(approved))
            current_requests.extend(self._requests_to_media_items(available))
        except Exception as e:
            logger.warning(f"Failed to get approved/available requests: {e}")
        
        current_keys = {item.unique_key for item in current_requests}
        
        # Get last known state
        user_state = self.state.get_user_state(mapping.plex_username)
        last_keys = user_state.last_seerr_requests
        
        # Find new requests
        new_keys = current_keys - last_keys
        new_items = [item for item in current_requests if item.unique_key in new_keys]
        
        logger.info(f"Found {len(new_items)} new Seerr requests for {mapping.seerr_username}")
        
        favorites_created = 0
        for item in new_items:
            if self.jellyfin.favorite_media_item(mapping.jellyfin_user_id, item):
                favorites_created += 1
                logger.info(f"Favorited in Jellyfin from Seerr request: {item}")
            else:
                logger.warning(f"Failed to favorite in Jellyfin: {item}")
        
        # Update state
        user_state.last_seerr_requests = current_keys
        
        return favorites_created
    
    def _requests_to_media_items(self, requests: List[dict]) -> List[MediaItem]:
        """Convert Seerr request objects to MediaItems."""
        items = []
        for req in requests:
            try:
                media = req.get('media', {})
                media_type = 'movie' if media.get('mediaType') == 'movie' else 'tv'
                
                item = MediaItem(
                    title=media.get('title', 'Unknown'),
                    year=media.get('releaseDate', {}).get('year') if media.get('releaseDate') else None,
                    media_type=media_type,
                    tmdb_id=media.get('tmdbId'),
                    tvdb_id=media.get('tvdbId')
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"Failed to convert request to MediaItem: {e}")
        return items
    
    def sync_user(self, mapping: UserMapping) -> dict:
        """Run all sync operations for a single user.
        
        Args:
            mapping: User mapping configuration
            
        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting sync for user: {mapping.plex_username}")
        
        results = {
            'plex_to_seerr': 0,
            'plex_to_jellyfin': 0,
            'seerr_to_jellyfin': 0,
            'errors': []
        }
        
        try:
            # Sync Plex watchlist -> Seerr requests
            results['plex_to_seerr'] = self.sync_plex_to_seerr(mapping)
        except Exception as e:
            logger.error(f"Plex->Seerr sync failed for {mapping.plex_username}: {e}")
            results['errors'].append(f"Plex->Seerr: {e}")
        
        try:
            # Sync Plex watchlist -> Jellyfin favorites
            results['plex_to_jellyfin'] = self.sync_plex_to_jellyfin(mapping)
        except Exception as e:
            logger.error(f"Plex->Jellyfin sync failed for {mapping.plex_username}: {e}")
            results['errors'].append(f"Plex->Jellyfin: {e}")
        
        try:
            # Sync Seerr requests -> Jellyfin favorites
            results['seerr_to_jellyfin'] = self.sync_seerr_to_jellyfin(mapping)
        except Exception as e:
            logger.error(f"Seerr->Jellyfin sync failed for {mapping.plex_username}: {e}")
            results['errors'].append(f"Seerr->Jellyfin: {e}")
        
        # Update sync time
        user_state = self.state.get_user_state(mapping.plex_username)
        user_state.last_sync_time = datetime.now()
        
        logger.info(f"Completed sync for {mapping.plex_username}: {results}")
        return results
    
    def run_sync(self) -> dict:
        """Run sync for all configured users.
        
        Returns:
            Dictionary with overall sync results
        """
        logger.info("Starting full sync")
        
        overall_results = {
            'users_synced': 0,
            'total_plex_to_seerr': 0,
            'total_plex_to_jellyfin': 0,
            'total_seerr_to_jellyfin': 0,
            'errors': []
        }
        
        # Populate user IDs first
        self._populate_user_ids()
        
        for mapping in self.user_mappings.mappings:
            try:
                user_results = self.sync_user(mapping)
                overall_results['users_synced'] += 1
                overall_results['total_plex_to_seerr'] += user_results['plex_to_seerr']
                overall_results['total_plex_to_jellyfin'] += user_results['plex_to_jellyfin']
                overall_results['total_seerr_to_jellyfin'] += user_results['seerr_to_jellyfin']
                overall_results['errors'].extend(user_results['errors'])
            except Exception as e:
                logger.error(f"Sync failed for {mapping.plex_username}: {e}")
                overall_results['errors'].append(f"{mapping.plex_username}: {e}")
        
        # Save state
        self.state.save(self.state_file)
        
        logger.info(f"Full sync complete: {overall_results}")
        return overall_results
    
    def health_check(self) -> dict:
        """Check health of all connected services.
        
        Returns:
            Dictionary with health status of each service
        """
        return {
            'plex': self.plex.health_check(),
            'jellyfin': self.jellyfin.health_check(),
            'seerr': self.seerr.health_check()
        }
