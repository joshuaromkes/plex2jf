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
from src.config.db_config import get_server_credentials, get_feature_flags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_sync_engine(db: Session = Depends(get_db)) -> SyncEngine | None:
    """Get sync engine instance using DB-stored server credentials."""
    plex = get_server_credentials(db, "plex")
    jellyfin = get_server_credentials(db, "jellyfin")
    seerr = get_server_credentials(db, "seerr")

    if not plex:
        logger.warning("No active Plex server configured")
        return None

    plex_client = PlexClient(token=plex["token"], url=plex["url"])
    jellyfin_client = JellyfinClient(
        url=jellyfin["url"], api_key=jellyfin["api_key"]
    ) if jellyfin else None
    seerr_client = SeerrClient(
        url=seerr["url"], api_key=seerr["api_key"]
    ) if seerr else None

    flags = get_feature_flags(db)
    class _Cfg:
        sync = type("s", (), {"features": type("f", (), flags)})()
    return SyncEngine(db, plex_client, jellyfin_client, seerr_client, _Cfg())


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
    if sync_engine is None:
        return {"status": "error", "message": "Sync engine unavailable — no Plex server configured"}
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
