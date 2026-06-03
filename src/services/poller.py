"""Polling service for Plex watchlists."""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from src.api.plex import PlexClient
from src.services.sync_engine import SyncEngine
from src.database.models import PollingState, UserMapping

logger = logging.getLogger(__name__)


class PollerService:
    """Service for polling Plex watchlists."""
    
    def __init__(
        self,
        db: Session,
        plex_client: PlexClient,
        sync_engine: SyncEngine,
    ):
        self.db = db
        self.plex = plex_client
        self.sync_engine = sync_engine
    
    def _get_mapped_usernames(self) -> List[str]:
        """Get list of mapped Plex usernames.
        
        Returns:
            List of Plex usernames that have mappings
        """
        mappings = self.db.query(UserMapping).filter(UserMapping.is_active == True).all()
        return [m.plex_username for m in mappings]
    
    def poll_plex_watchlists(self) -> int:
        """Poll Plex watchlists and sync items.
        
        Returns:
            Number of items synced
        """
        logger.info("Starting Plex watchlist poll...")
        
        try:
            # Get mapped usernames to filter by
            mapped_usernames = self._get_mapped_usernames()
            logger.info(f"Found {len(mapped_usernames)} mapped users: {mapped_usernames}")
            
            # Get watchlist items for mapped users only
            watchlist_items = self.plex.get_watchlist(mapped_usernames=mapped_usernames)
            
            synced_count = 0
            
            logger.info(f"Processing {len(watchlist_items)} watchlist items for sync")

            # Diagnostic logging: capture whether this SyncEngine instance has config/feature flags
            has_config_attr = hasattr(self.sync_engine, 'config')
            runtime_config = getattr(self.sync_engine, 'config', None)
            sync_config = getattr(runtime_config, 'sync', None) if runtime_config else None
            features_config = getattr(sync_config, 'features', None) if sync_config else None

            configured_seerr_flag = None
            configured_jellyfin_flag = None
            if features_config:
                configured_seerr_flag = getattr(features_config, 'plex_watchlist_to_seerr', None)
                configured_jellyfin_flag = getattr(features_config, 'plex_watchlist_to_jellyfin', None)

            logger.info(
                "Poller runtime config visibility: has_config_attr=%s config_present=%s sync_present=%s features_present=%s configured_seerr_flag=%s configured_jellyfin_flag=%s",
                has_config_attr,
                runtime_config is not None,
                sync_config is not None,
                features_config is not None,
                configured_seerr_flag,
                configured_jellyfin_flag,
            )

            # Effective feature flags
            seerr_enabled = bool(configured_seerr_flag) if configured_seerr_flag is not None else False
            jellyfin_enabled = bool(configured_jellyfin_flag) if configured_jellyfin_flag is not None else False

            logger.info(
                "Effective poller feature flags: seerr_enabled=%s jellyfin_enabled=%s",
                seerr_enabled,
                jellyfin_enabled,
            )
            
            for item in watchlist_items:
                # Determine media type
                media_type = 'movie' if item.type == 'movie' else 'tv'
                
                logger.info(
                    "Processing item: %s (%s) for user %s, TMDB=%s IMDB=%s TVDB=%s year=%s",
                    item.title,
                    media_type,
                    item.username,
                    item.tmdb_id,
                    item.imdb_id,
                    item.tvdb_id,
                    getattr(item, 'year', None),
                )
                
                # Sync to Seerr if enabled
                if seerr_enabled:
                    logger.info(f"Attempting Seerr sync for {item.title}")
                    success = self.sync_engine.sync_plex_watchlist_to_seerr(
                        item.username,
                        item.tmdb_id,
                        media_type,
                        item.title,
                        year=getattr(item, 'year', None),
                        imdb_id=item.imdb_id,
                        tvdb_id=item.tvdb_id,
                    )
                    if success:
                        synced_count += 1
                        logger.info(f"Successfully synced {item.title} to Seerr")
                    else:
                        logger.warning(f"Failed to sync {item.title} to Seerr")
                else:
                    logger.warning(f"Seerr sync not enabled, skipping {item.title}")

                if jellyfin_enabled:
                    success = self.sync_engine.sync_plex_watchlist_to_jellyfin(
                        item.username,
                        item.tmdb_id,
                        media_type,
                        item.title,
                    )
                    if success:
                        synced_count += 1
            
            # Update polling state
            self._update_polling_state('plex_watchlist', success=True)
            
            logger.info(f"Plex watchlist poll complete. Synced {synced_count} items.")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error polling Plex watchlists: {e}")
            self._update_polling_state('plex_watchlist', success=False)
            return 0
    
    def _update_polling_state(self, service: str, success: bool) -> None:
        """Update polling state in database.
        
        Args:
            service: Service name
            success: Whether the poll was successful
        """
        state = (
            self.db.query(PollingState)
            .filter(PollingState.service == service)
            .first()
        )
        
        if state:
            state.last_poll_at = datetime.now(timezone.utc)
            if success:
                state.last_success_at = datetime.now(timezone.utc)
                state.error_count = 0
            else:
                state.error_count += 1
        else:
            state = PollingState(
                service=service,
                last_poll_at=datetime.now(timezone.utc),
                last_success_at=datetime.now(timezone.utc) if success else None,
                error_count=0 if success else 1,
            )
            self.db.add(state)
        
        self.db.commit()
    
    def get_last_poll_time(self, service: str = 'plex_watchlist') -> Optional[datetime]:
        """Get last poll time for a service.
        
        Args:
            service: Service name
            
        Returns:
            Last poll time or None
        """
        state = (
            self.db.query(PollingState)
            .filter(PollingState.service == service)
            .first()
        )
        
        return state.last_poll_at if state else None
    
    def retry_pending_items(self) -> int:
        """Retry pending items from previous syncs.
        
        Returns:
            Number of items successfully synced
        """
        return self.sync_engine.retry_pending_items()

    def poll_seerr_requests_to_jellyfin(self) -> int:
        """Poll Seerr requests and sync completed/approved items to Jellyfin.

        Returns:
            Number of items synced to Jellyfin
        """
        logger.info("Starting Seerr request poll...")

        try:
            summary = self.sync_engine.sync_seerr_completed_to_jellyfin(
                statuses=['APPROVED', 'PROCESSING', 'AVAILABLE', 'FILLED']
            )
            synced_count = int(summary.get('synced', 0))
            self._update_polling_state('seerr_requests', success=True)
            logger.info("Seerr request poll complete. Summary: %s", summary)
            return synced_count
        except Exception as e:
            logger.error(f"Error polling Seerr requests: {e}")
            self._update_polling_state('seerr_requests', success=False)
            return 0
