"""Sync engine for coordinating sync operations."""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session

from src.api.plex import PlexClient, PlexWatchlistItem
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.database.models import SyncState, UserMapping, PollingState
from src.services.user_mapper import UserMapper

logger = logging.getLogger(__name__)


class SyncEngine:
    """Core sync engine for coordinating sync operations."""
    
    def __init__(
        self,
        db: Session,
        plex_client: PlexClient,
        jellyfin_client: JellyfinClient,
        seerr_client: SeerrClient,
        config=None,
    ):
        self.db = db
        self.plex = plex_client
        self.jellyfin = jellyfin_client
        self.seerr = seerr_client
        self.user_mapper = UserMapper(db)
        self.config = config
    
    def sync_seerr_request_to_jellyfin(
        self,
        seerr_user_id: str,
        media_type: str,
        tmdb_id: str,
        title: str,
        request_id: Optional[str] = None,
    ) -> bool:
        """Sync a Seerr request to Jellyfin favorite.
        
        Args:
            seerr_user_id: Seerr user ID
            media_type: 'movie' or 'tv'
            tmdb_id: TMDB ID
            title: Media title
            request_id: Optional Seerr request ID
            
        Returns:
            True if successful, False otherwise
        """
        # Get user mapping
        user_mapping = self.user_mapper.get_mapping_by_seerr_user_id(seerr_user_id)
        if not user_mapping:
            logger.warning(f"No user mapping found for Seerr user {seerr_user_id}")
            return False
        
        # Check if already synced
        existing = (
            self.db.query(SyncState)
            .filter(
                SyncState.user_mapping_id == user_mapping.id,
                SyncState.external_id == tmdb_id,
                SyncState.source == 'seerr_request',
            )
            .first()
        )
        
        if existing and existing.synced_to_jellyfin:
            logger.debug(f"Already synced to Jellyfin: {title} (TMDB: {tmdb_id})")
            return True
        
        # Search for item in Jellyfin
        jf_media_type = 'Movie' if media_type == 'movie' else 'Series'
        item = self.jellyfin.search_by_tmdb_id(tmdb_id, jf_media_type)
        
        if not item:
            # Item not in library yet, mark as pending
            if existing:
                existing.retry_count += 1
                existing.last_error = "Item not found in Jellyfin library"
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='seerr_request',
                    source_id=request_id,
                    retry_count=1,
                    last_error="Item not found in Jellyfin library",
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Item not in Jellyfin yet, marked as pending: {title}")
            return False
        
        # Favorite the item
        success = self.jellyfin.favorite_item(
            user_mapping.jellyfin_user_id,
            item['Id']
        )
        
        if success:
            # Update or create sync state
            if existing:
                existing.synced_to_jellyfin = True
                existing.jellyfin_item_id = item['Id']
                existing.last_synced_at = datetime.utcnow()
                existing.last_error = None
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='seerr_request',
                    source_id=request_id,
                    synced_to_jellyfin=True,
                    jellyfin_item_id=item['Id'],
                    last_synced_at=datetime.utcnow(),
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Favorited in Jellyfin: {title}")
            return True
        else:
            if existing:
                existing.retry_count += 1
                existing.last_error = "Failed to favorite item"
            self.db.commit()
            return False
    
    def sync_plex_watchlist_to_seerr(
        self,
        plex_username: str,
        tmdb_id: str,
        media_type: str,
        title: str,
    ) -> bool:
        """Sync Plex watchlist item to Seerr request.
        
        Args:
            plex_username: Plex username
            tmdb_id: TMDB ID
            media_type: 'movie' or 'tv'
            title: Media title
            
        Returns:
            True if successful, False otherwise
        """
        # Get user mapping
        logger.info(f"Looking up user mapping for Plex user: {plex_username}")
        user_mapping = self.user_mapper.get_mapping_by_plex_username(plex_username)
        if not user_mapping:
            logger.warning(f"No user mapping found for Plex user {plex_username}")
            # Log all available mappings for debugging
            all_mappings = self.user_mapper.get_all_mappings()
            available = [m.plex_username for m in all_mappings if m.is_active]
            logger.warning(f"Available active mappings: {available}")
            return False
        
        logger.info(f"Found user mapping: Plex={user_mapping.plex_username}, Seerr ID={user_mapping.seerr_user_id}")
        
        # Check if already synced
        existing = (
            self.db.query(SyncState)
            .filter(
                SyncState.user_mapping_id == user_mapping.id,
                SyncState.external_id == tmdb_id,
                SyncState.source == 'plex_watchlist',
            )
            .first()
        )
        
        if existing and existing.synced_to_seerr:
            logger.debug(f"Already synced to Seerr: {title} (TMDB: {tmdb_id})")
            return True

        # Guard against duplicate Seerr requests: if the request already exists
        # in Seerr, mark it synced locally and skip creating a new one.
        existing_request = None
        try:
            existing_request = self.seerr.find_existing_request(
                media_type='tv' if media_type == 'tv' else 'movie',
                media_id=int(tmdb_id),
                user_id=int(user_mapping.seerr_user_id),
            )
        except Exception as e:
            logger.warning(f"Failed to check existing Seerr requests for {title}: {e}")

        if existing_request:
            existing_request_id = str(existing_request.get('id')) if existing_request.get('id') is not None else None

            if existing:
                existing.synced_to_seerr = True
                existing.seerr_request_id = existing_request_id
                existing.last_synced_at = datetime.utcnow()
                existing.last_error = None
            else:
                self.db.add(
                    SyncState(
                        user_mapping_id=user_mapping.id,
                        media_type=media_type,
                        external_id=tmdb_id,
                        title=title,
                        source='plex_watchlist',
                        synced_to_seerr=True,
                        seerr_request_id=existing_request_id,
                        last_synced_at=datetime.utcnow(),
                    )
                )

            self.db.commit()
            logger.info(f"Seerr request already exists for {title}; marked as synced")
            return True
        
        # Create request in Seerr
        seerr_media_type = 'movie' if media_type == 'movie' else 'tv'
        logger.info(f"Creating Seerr request: {title} ({seerr_media_type}, TMDB:{tmdb_id}) for user {user_mapping.seerr_user_id}")
        
        try:
            result = self.seerr.create_request(
                media_type=seerr_media_type,
                media_id=int(tmdb_id),
                user_id=int(user_mapping.seerr_user_id),
            )
        except Exception as e:
            logger.error(f"Failed to create Seerr request: {e}", exc_info=True)
            result = None
        
        if result:
            request_id = str(result.get('id')) if result else None
            
            # Update or create sync state
            if existing:
                existing.synced_to_seerr = True
                existing.seerr_request_id = request_id
                existing.last_synced_at = datetime.utcnow()
                existing.last_error = None
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='plex_watchlist',
                    synced_to_seerr=True,
                    seerr_request_id=request_id,
                    last_synced_at=datetime.utcnow(),
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Created Seerr request: {title}")
            return True
        else:
            if existing:
                existing.retry_count += 1
                existing.last_error = "Failed to create Seerr request"
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='plex_watchlist',
                    retry_count=1,
                    last_error="Failed to create Seerr request",
                )
                self.db.add(new_state)
            
            self.db.commit()
            return False
    
    def sync_plex_watchlist_to_jellyfin(
        self,
        plex_username: str,
        tmdb_id: str,
        media_type: str,
        title: str,
    ) -> bool:
        """Sync Plex watchlist item to Jellyfin favorite.
        
        Args:
            plex_username: Plex username
            tmdb_id: TMDB ID
            media_type: 'movie' or 'tv'
            title: Media title
            
        Returns:
            True if successful, False otherwise
        """
        # Get user mapping
        user_mapping = self.user_mapper.get_mapping_by_plex_username(plex_username)
        if not user_mapping:
            logger.warning(f"No user mapping found for Plex user {plex_username}")
            return False
        
        # Check if already synced
        existing = (
            self.db.query(SyncState)
            .filter(
                SyncState.user_mapping_id == user_mapping.id,
                SyncState.external_id == tmdb_id,
                SyncState.source == 'plex_watchlist',
            )
            .first()
        )
        
        if existing and existing.synced_to_jellyfin:
            logger.debug(f"Already favorited in Jellyfin: {title} (TMDB: {tmdb_id})")
            return True
        
        # Search for item in Jellyfin
        jf_media_type = 'Movie' if media_type == 'movie' else 'Series'
        item = self.jellyfin.search_by_tmdb_id(tmdb_id, jf_media_type)
        
        if not item:
            # Item not in library yet
            if existing:
                existing.retry_count += 1
                existing.last_error = "Item not found in Jellyfin library"
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='plex_watchlist',
                    retry_count=1,
                    last_error="Item not found in Jellyfin library",
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Item not in Jellyfin yet, marked as pending: {title}")
            return False
        
        # Favorite the item
        success = self.jellyfin.favorite_item(
            user_mapping.jellyfin_user_id,
            item['Id']
        )
        
        if success:
            # Update or create sync state
            if existing:
                existing.synced_to_jellyfin = True
                existing.jellyfin_item_id = item['Id']
                existing.last_synced_at = datetime.utcnow()
                existing.last_error = None
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='plex_watchlist',
                    synced_to_jellyfin=True,
                    jellyfin_item_id=item['Id'],
                    last_synced_at=datetime.utcnow(),
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Favorited in Jellyfin: {title}")
            return True
        else:
            if existing:
                existing.retry_count += 1
                existing.last_error = "Failed to favorite item"
            self.db.commit()
            return False
    
    def retry_pending_items(self, max_age_days: int = 7) -> int:
        """Retry syncing pending items.
        
        Args:
            max_age_days: Maximum age of items to retry
            
        Returns:
            Number of items successfully synced
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        pending = (
            self.db.query(SyncState)
            .filter(
                SyncState.synced_to_jellyfin == False,
                SyncState.first_seen_at > cutoff_date,
                SyncState.retry_count < 10,
            )
            .all()
        )
        
        success_count = 0
        
        for item in pending:
            user_mapping = (
                self.db.query(UserMapping)
                .filter(UserMapping.id == item.user_mapping_id)
                .first()
            )
            
            if not user_mapping:
                continue
            
            # Try to sync based on source
            if item.source == 'seerr_request':
                success = self.sync_seerr_request_to_jellyfin(
                    user_mapping.seerr_user_id,
                    item.media_type,
                    item.external_id,
                    item.title or "Unknown",
                    item.source_id,
                )
            elif item.source == 'plex_watchlist':
                success = self.sync_plex_watchlist_to_jellyfin(
                    user_mapping.plex_username,
                    item.external_id,
                    item.media_type,
                    item.title or "Unknown",
                )
            else:
                continue
            
            if success:
                success_count += 1
        
        return success_count
    
    def get_stats(self) -> dict:
        """Get sync statistics.
        
        Returns:
            Dictionary with sync statistics
        """
        total = self.db.query(SyncState).count()
        synced_jf = self.db.query(SyncState).filter(SyncState.synced_to_jellyfin == True).count()
        synced_seerr = self.db.query(SyncState).filter(SyncState.synced_to_seerr == True).count()
        pending = self.db.query(SyncState).filter(SyncState.synced_to_jellyfin == False).count()
        
        return {
            'total_items': total,
            'synced_to_jellyfin': synced_jf,
            'synced_to_seerr': synced_seerr,
            'pending': pending,
        }
