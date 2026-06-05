"""System API routes."""
import logging
import platform
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import ServerConfig
from src._version import __version__

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"])


class HealthStatus(BaseModel):
    """Schema for health check response."""
    status: str
    timestamp: datetime
    database: str
    servers: dict


class SystemInfo(BaseModel):
    """Schema for system information."""
    version: str
    python_version: str
    platform: str
    database_type: str


class LogEntry(BaseModel):
    """Schema for log entry."""
    timestamp: str
    level: str
    message: str


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Get system health status."""
    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        database_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_status = "unhealthy"
    
    # Check server connections
    servers = db.query(ServerConfig).all()
    server_statuses = {}

    for server in servers:
        server_statuses[server.service_type] = {
            "configured": True,
            "connected": server.last_test_status == "success",
            "last_test": server.last_test_at.replace(tzinfo=timezone.utc).isoformat() if server.last_test_at else None
        }
    
    # Determine overall status
    overall_status = "healthy"
    if database_status != "healthy":
        overall_status = "unhealthy"
    elif any(not s["connected"] for s in server_statuses.values()):
        overall_status = "degraded"
    
    return {
        "success": True,
        "data": {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": database_status,
            "servers": server_statuses
        }
    }


@router.get("/info")
async def system_info():
    """Get system information."""
    import sys
    
    return {
        "success": True,
        "data": {
            "version": __version__,
            "python_version": sys.version,
            "platform": platform.platform(),
            "database_type": "SQLite"
        }
    }


@router.get("/logs")
async def get_logs(
    lines: int = 100,
    level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get recent application logs.
    
    Note: This is a placeholder. In a production environment,
    you would read from the actual log file or use a log aggregation service.
    """
    # For now, return empty logs - this would need to read from the log file
    # in a real implementation
    return {
        "success": True,
        "data": {
            "logs": [],
            "total": 0,
            "lines_requested": lines
        }
    }