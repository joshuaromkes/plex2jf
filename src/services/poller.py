"""Polling service for Plex watchlists."""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.api.plex import PlexClient
from src.services.sync_engine import SyncEngine
from src.database.models import PollingState

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
    
    def poll_plex_watchlists(self) -> int:
        """Poll Plex watchlists and sync items.
        
        Returns:
            Number of items synced
        """
        logger.info("Starting Plex watchlist poll...")
        
        try:
            # Get watchlist items for all users
            watchlist_items = self.plex.get_watchlist()
            
            synced_count = 0
            
            for item in watchlist_items:
                # Determine media type
                media_type = 'movie' if item.type == 'movie' else 'tv'
                
                # Skip if no TMDB ID
                if not item.tmdb_id:
                    logger.warning(f"No TMDB ID for {item.title}, skipping")
                    continue
                
                # Sync to Seerr if enabled
                if hasattr(self.sync_engine, 'config') and self.sync_engine.config.sync.features.plex_watchlist_to_seerr:
                    success = self.sync_engine.sync_plex_watchlist_to_seerr(
                        item.username,
                        item.tmdb_id,
                        media_type,
                        item.title,
                    )
                    if success:
                        synced_count += 1
                
                # Sync to Jellyfin if enabled
                if hasattr(self.sync_engine, 'config') and self.sync_engine.config.sync.features.plex_watchlist_to_jellyfin:
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
            state.last_poll_at = datetime.utcnow()
            if success:
                state.last_success_at = datetime.utcnow()
                state.error_count = 0
            else:
                state.error_count += 1
        else:
            state = PollingState(
                service=service,
                last_poll_at=datetime.utcnow(),
                last_success_at=datetime.utcnow() if success else None,
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