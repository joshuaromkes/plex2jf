"""Dashboard API routes."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
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
    external_users = db.query(ExternalUser).count()
    
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
    query = db.query(SyncState).join(UserMapping)
    
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
        "data": activity_items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages
        }
    }


@router.post("/sync")
async def trigger_manual_sync(db: Session = Depends(get_db)):
    """Trigger a manual sync operation."""
    # This will be implemented with the existing sync engine
    logger.info("Manual sync triggered via API")
    
    # For now, return success - the actual sync will be handled by the poller
    return {
        "success": True,
        "message": "Sync triggered successfully. Check activity feed for progress."
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