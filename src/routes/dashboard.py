"""Dashboard API routes."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import (
    ServerConfig, 
    UserMapping, 
    SyncState, 
    ExternalUser,
    WebhookEvent
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    servers_connected: int
    servers_total: int
    users_mapped: int
    users_total: int
    items_synced: int
    items_pending: int
    items_failed: int
    seerr_request: Dict[str, Any]


class ActivityItem(BaseModel):
    """Schema for activity feed item."""
    id: int
    title: str
    media_type: str
    status: str  # 'synced', 'pending', 'failed'
    source: str
    user: str
    timestamp: datetime
    error: Optional[str] = None


class ActivityResponse(BaseModel):
    """Schema for activity response."""
    items: List[ActivityItem]
    page: int
    per_page: int
    total: int
    pages: int


class SyncTriggerResponse(BaseModel):
    """Schema for sync trigger response."""
    success: bool
    message: str


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall dashboard statistics."""
    # Server stats
    servers_total = db.query(ServerConfig).count()
    servers_connected = db.query(ServerConfig).filter(
        ServerConfig.last_test_status == "success"
    ).count()
    
    # User stats
    users_mapped = db.query(UserMapping).filter(UserMapping.is_active == True).count()
    
    # Count uniquely mapped users, not just ExternalUser entries
    # This ensures the count of "total external users" is accurate and not duplicated
    plex_users = db.query(func.count(func.distinct(ExternalUser.external_id))).filter(
        ExternalUser.service_type == "plex"
    ).scalar() or 0
    
    jellyfin_users = db.query(func.count(func.distinct(ExternalUser.external_id))).filter(
        ExternalUser.service_type == "jellyfin"
    ).scalar() or 0
    
    seerr_users = db.query(func.count(func.distinct(ExternalUser.external_id))).filter(
        ExternalUser.service_type == "seerr"
    ).scalar() or 0
    
    external_users = plex_users + jellyfin_users + seerr_users
    
    # Sync stats
    items_synced = db.query(SyncState).filter(
        SyncState.synced_to_jellyfin == True
    ).count()
    
    items_pending = db.query(SyncState).filter(
        SyncState.synced_to_jellyfin == False,
        SyncState.retry_count < 3
    ).count()
    
    items_failed = db.query(SyncState).filter(
        SyncState.synced_to_jellyfin == False,
        SyncState.retry_count >= 3
    ).count()

    # Last sync timestamps
    from src.database.models import PollingState
    plex_poll = db.query(PollingState).filter(PollingState.service == 'plex_watchlist').first()
    seerr_poll = db.query(PollingState).filter(PollingState.service == 'seerr_requests').first()

    # Helper: SQLite stores naive UTC datetimes; mark them with tzinfo so
    # isoformat() renders a timezone suffix the frontend can parse correctly.
    from datetime import timezone as tz
    def _utc_iso(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.utc)
        return dt.isoformat()

    last_sync = None
    if plex_poll and plex_poll.last_success_at:
        last_sync = _utc_iso(plex_poll.last_success_at)
    elif seerr_poll and seerr_poll.last_success_at:
        last_sync = _utc_iso(seerr_poll.last_success_at)
    
    # Seerr request specific stats (includes both mapped and unmapped)
    seerr_query = db.query(SyncState).filter(SyncState.source == 'seerr_request')
    seerr_total = seerr_query.count()
    seerr_synced = seerr_query.filter(SyncState.synced_to_jellyfin == True).count()
    seerr_pending = seerr_query.filter(
        SyncState.synced_to_jellyfin == False,
        SyncState.retry_count < 3,
    ).count()
    seerr_failed = seerr_query.filter(
        SyncState.synced_to_jellyfin == False,
        SyncState.retry_count >= 3,
    ).count()

    # Unmapped stats (user_mapping_id IS NULL)
    unmapped_query = db.query(SyncState).filter(SyncState.user_mapping_id == None)
    unmapped_total = unmapped_query.count()
    unmapped_synced = unmapped_query.filter(SyncState.synced_to_jellyfin == True).count()
    unmapped_pending = unmapped_query.filter(
        SyncState.synced_to_jellyfin == False,
        SyncState.retry_count < 3,
    ).count()
    unmapped_failed = unmapped_query.filter(
        SyncState.synced_to_jellyfin == False,
        SyncState.retry_count >= 3,
    ).count()
    
    return {
        "success": True,
        "data": {
            "servers_connected": servers_connected,
            "servers_total": servers_total,
            "users_mapped": users_mapped,
            "users_total": external_users,
            "items_synced": items_synced,
            "items_pending": items_pending,
            "items_failed": items_failed,
            "last_sync": last_sync,
            "seerr_request": {
                "total": seerr_total,
                "synced": seerr_synced,
                "pending": seerr_pending,
                "failed": seerr_failed,
            },
            "unmapped": {
                "total": unmapped_total,
                "synced": unmapped_synced,
                "pending": unmapped_pending,
                "failed": unmapped_failed,
            }
        }
    }


@router.get("/activity")
async def get_activity_feed(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get recent activity feed."""
    query = db.query(SyncState).outerjoin(UserMapping)
    
    # Apply filters
    if status:
        if status == "synced":
            query = query.filter(SyncState.synced_to_jellyfin == True)
        elif status == "pending":
            query = query.filter(
                SyncState.synced_to_jellyfin == False,
                SyncState.retry_count < 3
            )
        elif status == "failed":
            query = query.filter(
                SyncState.synced_to_jellyfin == False,
                SyncState.retry_count >= 3
            )
    
    if source:
        query = query.filter(SyncState.source == source)
    
    # Order by most recent
    query = query.order_by(SyncState.first_seen_at.desc())
    
    # Get total count
    total = query.count()
    pages = (total + per_page - 1) // per_page
    
    # Paginate
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    
    # Format response
    activity_items = []
    for item in items:
        # Determine status
        if item.synced_to_jellyfin:
            item_status = "synced"
        elif item.retry_count >= 3:
            item_status = "failed"
        else:
            item_status = "pending"
        
        activity_items.append({
            "id": item.id,
            "title": item.title or "Unknown",
            "media_type": item.media_type,
            "status": item_status,
            "source": item.source,
            "user": item.user_mapping.plex_username if item.user_mapping else "Unknown",
            "timestamp": item.first_seen_at,
            "error": item.last_error
        })
    
    return {
        "success": True,
        "data": {
            "items": activity_items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages
        }
    }


@router.post("/sync")
async def trigger_manual_sync(db: Session = Depends(get_db)):
    """Trigger a manual sync operation."""
    from src.api.plex import PlexClient
    from src.api.jellyfin import JellyfinClient
    from src.api.seerr import SeerrClient
    from src.services.sync_engine import SyncEngine
    from src.services.poller import PollerService
    
    logger.info("Manual sync triggered via API")
    
    try:
        # Get server configs from database
        plex_server = db.query(ServerConfig).filter(
            ServerConfig.service_type == "plex",
            ServerConfig.is_active == True
        ).first()
        
        jellyfin_server = db.query(ServerConfig).filter(
            ServerConfig.service_type == "jellyfin",
            ServerConfig.is_active == True
        ).first()
        
        seerr_server = db.query(ServerConfig).filter(
            ServerConfig.service_type == "seerr",
            ServerConfig.is_active == True
        ).first()
        
        if not plex_server:
            return {
                "success": False,
                "error": {"message": "No active Plex server configured"}
            }
        
        # Create clients
        plex_client = PlexClient(token=plex_server.token, url=plex_server.url)
        jellyfin_client = JellyfinClient(url=jellyfin_server.url, api_key=jellyfin_server.api_key) if jellyfin_server else None
        seerr_client = SeerrClient(url=seerr_server.url, api_key=seerr_server.api_key) if seerr_server else None

        # Feature flags from DB settings
        from src.config.db_config import get_feature_flags
        flags = get_feature_flags(db)
        class _Cfg:
            sync = type("s", (), {"features": type("f", (), flags)})()
        sync_engine = SyncEngine(db, plex_client, jellyfin_client, seerr_client, _Cfg())
        poller = PollerService(db, plex_client, sync_engine)
        
        # Run the syncs
        watchlist_count = poller.poll_plex_watchlists()

        seerr_count = 0
        if flags.get("seerr_to_jellyfin") and seerr_client:
            seerr_count = poller.poll_seerr_requests_to_jellyfin(
                include_unmapped=bool(flags.get("sync_unmapped_seerr")),
            )

        # Retry pending items
        retry_count = sync_engine.retry_pending_items()

        return {
            "success": True,
            "message": f"Sync completed. {watchlist_count} watchlist items, {seerr_count} Seerr requests synced.",
            "data": {
                "synced_items": watchlist_count,
                "seerr_synced": seerr_count,
                "retried": retry_count,
            }
        }
    except Exception as e:
        logger.error(f"Error during manual sync: {e}")
        return {
            "success": False,
            "error": {"message": str(e)}
        }


@router.post("/retry")
async def retry_pending_items(db: Session = Depends(get_db)):
    """Retry all pending items."""
    pending_items = db.query(SyncState).filter(
        SyncState.synced_to_jellyfin == False,
        SyncState.retry_count < 3
    ).all()
    
    count = len(pending_items)
    
    # Reset retry count for pending items
    for item in pending_items:
        item.retry_count = 0
        item.last_error = None
    
    db.commit()
    
    logger.info(f"Retry triggered for {count} pending items")
    
    return {
        "success": True,
        "message": f"Retry triggered for {count} pending items"
    }


@router.post("/retry/{item_id}")
async def retry_item(item_id: int, db: Session = Depends(get_db)):
    """Retry a specific item."""
    item = db.query(SyncState).filter(SyncState.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Reset retry count
    item.retry_count = 0
    item.last_error = None
    db.commit()
    
    logger.info(f"Retry triggered for item {item_id}")
    
    return {
        "success": True,
        "message": f"Retry triggered for item '{item.title or 'Unknown'}'"
    }
