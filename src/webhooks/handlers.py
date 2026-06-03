"""Webhook handlers for external services."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from src.database.models import WebhookEvent
from src.services.sync_engine import SyncEngine

logger = logging.getLogger(__name__)


class SeerrWebhookHandler:
    """Handler for Seerr webhook events."""
    
    def __init__(self, db: Session, sync_engine: SyncEngine):
        self.db = db
        self.sync_engine = sync_engine
    
    def handle_event(self, payload: Dict[str, Any]) -> bool:
        """Handle a Seerr webhook event.
        
        Args:
            payload: Webhook payload
            
        Returns:
            True if handled successfully, False otherwise
        """
        # Log the event
        event_type = payload.get('notification_type', 'UNKNOWN')
        event = WebhookEvent(
            event_type=event_type,
            payload=json.dumps(payload),
            processed=False,
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Received Seerr webhook: {event_type}")
        
        # Only process request events
        if event_type not in ['REQUEST_PENDING', 'REQUEST_APPROVED']:
            logger.debug(f"Ignoring event type: {event_type}")
            event.processed = True
            event.processed_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        
        try:
            # Extract data from payload
            request_data = payload.get('request', {})
            media_data = payload.get('media', {})
            
            seerr_user_id = str(request_data.get('requestedBy_userId') or request_data.get('requestedBy', {}).get('id'))
            media_type = media_data.get('media_type')
            tmdb_id = media_data.get('tmdbId')
            tvdb_id = media_data.get('tvdbId')
            title = payload.get('subject', 'Unknown')
            request_id = str(request_data.get('request_id') or request_data.get('id'))
            
            if not tmdb_id and tvdb_id:
                logger.warning(f"TVDB ID provided but TMDB ID needed: {title}")
                event.error = "TVDB ID provided but TMDB ID needed"
                event.processed_at = datetime.now(timezone.utc)
                self.db.commit()
                return False
            
            if not tmdb_id:
                logger.warning(f"No TMDB ID in webhook payload: {title}")
                event.error = "No TMDB ID in payload"
                event.processed_at = datetime.now(timezone.utc)
                self.db.commit()
                return False
            
            # Sync to Jellyfin
            success = self.sync_engine.sync_seerr_request_to_jellyfin(
                seerr_user_id=seerr_user_id,
                media_type=media_type,
                tmdb_id=str(tmdb_id),
                title=title,
                request_id=request_id,
            )
            
            event.processed = True
            event.processed_at = datetime.now(timezone.utc)
            self.db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing Seerr webhook: {e}")
            event.error = str(e)
            event.processed_at = datetime.now(timezone.utc)
            self.db.commit()
            return False
    
    def retry_failed_events(self) -> int:
        """Retry failed webhook events.
        
        Returns:
            Number of events successfully processed
        """
        failed_events = (
            self.db.query(WebhookEvent)
            .filter(
                WebhookEvent.processed == False,
                WebhookEvent.error != None,
            )
            .all()
        )
        
        success_count = 0
        
        for event in failed_events:
            try:
                payload = json.loads(event.payload)
                if self.handle_event(payload):
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to retry event {event.id}: {e}")
        
        return success_count