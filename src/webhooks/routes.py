"""Webhook routes for FastAPI."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.webhooks.handlers import SeerrWebhookHandler
from src.services.sync_engine import SyncEngine
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.config.settings import load_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_sync_engine(db: Session = Depends(get_db)) -> SyncEngine:
    """Get sync engine instance."""
    config = load_config()
    
    plex_client = PlexClient(
        token=config.plex.token,
        url=config.plex.url,
    )
    jellyfin_client = JellyfinClient(
        url=config.jellyfin.url,
        api_key=config.jellyfin.api_key,
    )
    seerr_client = SeerrClient(
        url=config.seerr.url,
        api_key=config.seerr.api_key,
    )
    
    return SyncEngine(db, plex_client, jellyfin_client, seerr_client)


@router.post("/seerr")
async def seerr_webhook(
    request: Request,
    db: Session = Depends(get_db),
    sync_engine: SyncEngine = Depends(get_sync_engine),
) -> Dict[str, Any]:
    """Receive Seerr webhook events.
    
    Configure in Seerr:
    - URL: http://plex2jf:8000/webhooks/seerr
    - Events: REQUEST_PENDING, REQUEST_APPROVED
    """
    try:
        payload = await request.json()
        logger.debug(f"Received Seerr webhook: {payload}")
        
        handler = SeerrWebhookHandler(db, sync_engine)
        success = handler.handle_event(payload)
        
        if success:
            return {"status": "success", "message": "Event processed"}
        else:
            # Return 200 even on failure to prevent Seerr from retrying
            # The event is logged and can be retried manually
            return {"status": "accepted", "message": "Event accepted but processing failed"}
            
    except Exception as e:
        logger.error(f"Error handling Seerr webhook: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "webhooks"}