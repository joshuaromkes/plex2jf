"""Server management API routes."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import ServerConfig
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.utils.response import success_response, error_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/servers", tags=["servers"])


def _utc_iso(dt):
    """Serialize naive UTC datetime with tzinfo so frontend parses correctly."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def server_to_dict(server: ServerConfig) -> dict:
    """Convert ServerConfig model to dictionary for JSON serialization."""
    return {
        "id": server.id,
        "service_type": server.service_type,
        "name": server.name,
        "url": server.url,
        "api_key": server.api_key,
        "token": server.token,
        "is_active": server.is_active,
        "last_test_at": _utc_iso(server.last_test_at),
        "last_test_status": server.last_test_status,
        "created_at": _utc_iso(server.created_at),
        "updated_at": _utc_iso(server.updated_at),
    }


class ServerConfigCreate(BaseModel):
    """Schema for creating a server config."""
    service_type: str = Field(..., pattern="^(plex|jellyfin|seerr)$")
    name: str
    url: str
    api_key: Optional[str] = None
    token: Optional[str] = None
    is_active: bool = True


class ServerConfigUpdate(BaseModel):
    """Schema for updating a server config."""
    name: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    is_active: Optional[bool] = None


class ServerConfigResponse(BaseModel):
    """Schema for server config response."""
    id: int
    service_type: str
    name: str
    url: str
    api_key: Optional[str] = None
    token: Optional[str] = None
    is_active: bool
    last_test_at: Optional[datetime] = None
    last_test_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServerTestResponse(BaseModel):
    """Schema for server test response."""
    success: bool
    message: str


@router.get("")
async def list_servers(db: Session = Depends(get_db)):
    """List all configured servers."""
    servers = db.query(ServerConfig).all()
    return JSONResponse(content=success_response([server_to_dict(s) for s in servers]))


@router.post("")
async def create_server(config: ServerConfigCreate, db: Session = Depends(get_db)):
    """Add a new server configuration."""
    # Check if a server of this type already exists (only one per type allowed for now)
    existing = db.query(ServerConfig).filter(
        ServerConfig.service_type == config.service_type
    ).first()
    
    if existing:
        return JSONResponse(
            status_code=200,  # Change to 200 so frontend handles it normally
            content=error_response(
                f"A {config.service_type} server is already configured. Please update it instead.",
                code="duplicate_server"
            )
        )
    
    server = ServerConfig(**config.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    
    logger.info(f"Created {config.service_type} server config: {config.name}")
    return JSONResponse(content=success_response(server_to_dict(server)))


@router.get("/{server_id}")
async def get_server(server_id: int, db: Session = Depends(get_db)):
    """Get a specific server configuration."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        return JSONResponse(
            status_code=404,
            content=error_response("Server not found", code="not_found")
        )
    return JSONResponse(content=success_response(server_to_dict(server)))


@router.put("/{server_id}")
async def update_server(
    server_id: int,
    config: ServerConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update a server configuration."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        return JSONResponse(
            status_code=404,
            content=error_response("Server not found", code="not_found")
        )
    
    # Update only provided fields
    update_data = config.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)
    
    server.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(server)
    
    logger.info(f"Updated server config: {server.name}")
    return JSONResponse(content=success_response(server_to_dict(server)))


@router.delete("/{server_id}")
async def delete_server(server_id: int, db: Session = Depends(get_db)):
    """Delete a server configuration."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        return JSONResponse(
            status_code=404,
            content=error_response("Server not found", code="not_found")
        )
    
    db.delete(server)
    db.commit()
    
    logger.info(f"Deleted server config: {server.name}")
    return JSONResponse(content=success_response(message="Server deleted successfully"))


@router.post("/{server_id}/test")
async def test_server_connection(server_id: int, db: Session = Depends(get_db)):
    """Test connection to a server."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        return JSONResponse(
            status_code=404,
            content=error_response("Server not found", code="not_found")
        )
    
    try:
        if server.service_type == "plex":
            if not server.token:
                return JSONResponse(
                    status_code=400,
                    content=error_response("Plex token is required", code="missing_token")
                )
            client = PlexClient(token=server.token, url=server.url)
            client.test_connection()
            
        elif server.service_type == "jellyfin":
            if not server.api_key:
                return JSONResponse(
                    status_code=400,
                    content=error_response("Jellyfin API key is required", code="missing_api_key")
                )
            client = JellyfinClient(url=server.url, api_key=server.api_key)
            client.test_connection()
            
        elif server.service_type == "seerr":
            if not server.api_key:
                return JSONResponse(
                    status_code=400,
                    content=error_response("Seerr API key is required", code="missing_api_key")
                )
            client = SeerrClient(url=server.url, api_key=server.api_key)
            client.test_connection()
        
        # Update test status
        server.last_test_at = datetime.now(timezone.utc)
        server.last_test_status = "success"
        db.commit()
        
        return JSONResponse(content=success_response(
            {"success": True, "message": "Connection successful"},
            message="Connection successful"
        ))
        
    except Exception as e:
        # Update test status
        server.last_test_at = datetime.now(timezone.utc)
        server.last_test_status = "failed"
        db.commit()
        
        logger.error(f"Server connection test failed for {server.name}: {e}")
        return JSONResponse(content=success_response(
            {"success": False, "message": f"Connection failed: {str(e)}"},
            message=f"Connection failed: {str(e)}"
        ))