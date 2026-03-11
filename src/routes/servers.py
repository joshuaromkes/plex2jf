"""Server management API routes."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import ServerConfig
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/servers", tags=["servers"])


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


@router.get("", response_model=List[ServerConfigResponse])
async def list_servers(db: Session = Depends(get_db)):
    """List all configured servers."""
    servers = db.query(ServerConfig).all()
    return servers


@router.post("", response_model=ServerConfigResponse)
async def create_server(config: ServerConfigCreate, db: Session = Depends(get_db)):
    """Add a new server configuration."""
    # Check if a server of this type already exists (only one per type allowed for now)
    existing = db.query(ServerConfig).filter(
        ServerConfig.service_type == config.service_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A {config.service_type} server is already configured. Please update it instead."
        )
    
    server = ServerConfig(**config.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    
    logger.info(f"Created {config.service_type} server config: {config.name}")
    return server


@router.get("/{server_id}", response_model=ServerConfigResponse)
async def get_server(server_id: int, db: Session = Depends(get_db)):
    """Get a specific server configuration."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.put("/{server_id}", response_model=ServerConfigResponse)
async def update_server(
    server_id: int, 
    config: ServerConfigUpdate, 
    db: Session = Depends(get_db)
):
    """Update a server configuration."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Update only provided fields
    update_data = config.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)
    
    server.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(server)
    
    logger.info(f"Updated server config: {server.name}")
    return server


@router.delete("/{server_id}")
async def delete_server(server_id: int, db: Session = Depends(get_db)):
    """Delete a server configuration."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    db.delete(server)
    db.commit()
    
    logger.info(f"Deleted server config: {server.name}")
    return {"success": True, "message": "Server deleted successfully"}


@router.post("/{server_id}/test", response_model=ServerTestResponse)
async def test_server_connection(server_id: int, db: Session = Depends(get_db)):
    """Test connection to a server."""
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    try:
        if server.service_type == "plex":
            if not server.token:
                raise HTTPException(status_code=400, detail="Plex token is required")
            client = PlexClient(token=server.token, url=server.url)
            client.test_connection()
            
        elif server.service_type == "jellyfin":
            if not server.api_key:
                raise HTTPException(status_code=400, detail="Jellyfin API key is required")
            client = JellyfinClient(url=server.url, api_key=server.api_key)
            client.test_connection()
            
        elif server.service_type == "seerr":
            if not server.api_key:
                raise HTTPException(status_code=400, detail="Seerr API key is required")
            client = SeerrClient(url=server.url, api_key=server.api_key)
            client.test_connection()
        
        # Update test status
        server.last_test_at = datetime.utcnow()
        server.last_test_status = "success"
        db.commit()
        
        return ServerTestResponse(success=True, message="Connection successful")
        
    except Exception as e:
        # Update test status
        server.last_test_at = datetime.utcnow()
        server.last_test_status = "failed"
        db.commit()
        
        logger.error(f"Server connection test failed for {server.name}: {e}")
        return ServerTestResponse(success=False, message=f"Connection failed: {str(e)}")