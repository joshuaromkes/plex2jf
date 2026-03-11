"""User management API routes."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import UserMapping, ExternalUser, ServerConfig
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


class UserMappingCreate(BaseModel):
    """Schema for creating a user mapping."""
    plex_username: str
    plex_user_id: Optional[str] = None
    jellyfin_user_id: str
    seerr_user_id: str
    is_active: bool = True
    notes: Optional[str] = None


class UserMappingUpdate(BaseModel):
    """Schema for updating a user mapping."""
    plex_username: Optional[str] = None
    plex_user_id: Optional[str] = None
    jellyfin_user_id: Optional[str] = None
    seerr_user_id: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class UserMappingResponse(BaseModel):
    """Schema for user mapping response."""
    id: int
    plex_username: str
    plex_user_id: Optional[str] = None
    jellyfin_user_id: str
    seerr_user_id: str
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExternalUserResponse(BaseModel):
    """Schema for external user response."""
    id: int
    service_type: str
    external_id: str
    username: str
    email: Optional[str] = None
    last_synced_at: datetime

    class Config:
        from_attributes = True


class ExternalUserList(BaseModel):
    """Schema for list of external users by service."""
    plex: List[ExternalUserResponse]
    jellyfin: List[ExternalUserResponse]
    seerr: List[ExternalUserResponse]


@router.get("/mappings", response_model=List[UserMappingResponse])
async def list_user_mappings(db: Session = Depends(get_db)):
    """Get all user mappings."""
    mappings = db.query(UserMapping).all()
    return mappings


@router.post("/mappings", response_model=UserMappingResponse)
async def create_user_mapping(mapping: UserMappingCreate, db: Session = Depends(get_db)):
    """Create a new user mapping."""
    # Check if mapping already exists for this plex username
    existing = db.query(UserMapping).filter(
        UserMapping.plex_username == mapping.plex_username
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A mapping for Plex user '{mapping.plex_username}' already exists"
        )
    
    new_mapping = UserMapping(**mapping.model_dump())
    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)
    
    logger.info(f"Created user mapping for {mapping.plex_username}")
    return new_mapping


@router.put("/mappings/{mapping_id}", response_model=UserMappingResponse)
async def update_user_mapping(
    mapping_id: int,
    mapping: UserMappingUpdate,
    db: Session = Depends(get_db)
):
    """Update a user mapping."""
    existing = db.query(UserMapping).filter(UserMapping.id == mapping_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="User mapping not found")
    
    # Update only provided fields
    update_data = mapping.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    
    existing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(existing)
    
    logger.info(f"Updated user mapping for {existing.plex_username}")
    return existing


@router.delete("/mappings/{mapping_id}")
async def delete_user_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """Delete a user mapping."""
    mapping = db.query(UserMapping).filter(UserMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="User mapping not found")
    
    db.delete(mapping)
    db.commit()
    
    logger.info(f"Deleted user mapping for {mapping.plex_username}")
    return {"success": True, "message": "User mapping deleted successfully"}


@router.get("/plex", response_model=List[ExternalUserResponse])
async def get_plex_users(db: Session = Depends(get_db)):
    """Fetch users from Plex API."""
    # First try to get from cache
    cached = db.query(ExternalUser).filter(ExternalUser.service_type == "plex").all()
    if cached:
        return cached
    
    # Try to fetch from Plex if server is configured
    server = db.query(ServerConfig).filter(
        ServerConfig.service_type == "plex",
        ServerConfig.is_active == True
    ).first()
    
    if not server:
        raise HTTPException(status_code=400, detail="No Plex server configured")
    
    try:
        client = PlexClient(token=server.token, url=server.url)
        users = client.get_users()
        
        # Cache users in database
        for user in users:
            external_user = ExternalUser(
                service_type="plex",
                external_id=str(user.get("id", "")),
                username=user.get("username", ""),
                email=user.get("email")
            )
            db.add(external_user)
        
        db.commit()
        
        # Return cached users
        return db.query(ExternalUser).filter(ExternalUser.service_type == "plex").all()
        
    except Exception as e:
        logger.error(f"Failed to fetch Plex users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Plex users: {str(e)}")


@router.get("/jellyfin", response_model=List[ExternalUserResponse])
async def get_jellyfin_users(db: Session = Depends(get_db)):
    """Fetch users from Jellyfin API."""
    # First try to get from cache
    cached = db.query(ExternalUser).filter(ExternalUser.service_type == "jellyfin").all()
    if cached:
        return cached
    
    # Try to fetch from Jellyfin if server is configured
    server = db.query(ServerConfig).filter(
        ServerConfig.service_type == "jellyfin",
        ServerConfig.is_active == True
    ).first()
    
    if not server:
        raise HTTPException(status_code=400, detail="No Jellyfin server configured")
    
    try:
        client = JellyfinClient(url=server.url, api_key=server.api_key)
        users = client.get_users()
        
        # Cache users in database
        for user in users:
            external_user = ExternalUser(
                service_type="jellyfin",
                external_id=str(user.get("Id", "")),
                username=user.get("Name", ""),
                email=user.get("ConnectUserName")
            )
            db.add(external_user)
        
        db.commit()
        
        # Return cached users
        return db.query(ExternalUser).filter(ExternalUser.service_type == "jellyfin").all()
        
    except Exception as e:
        logger.error(f"Failed to fetch Jellyfin users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Jellyfin users: {str(e)}")


@router.get("/seerr", response_model=List[ExternalUserResponse])
async def get_seerr_users(db: Session = Depends(get_db)):
    """Fetch users from Seerr API."""
    # First try to get from cache
    cached = db.query(ExternalUser).filter(ExternalUser.service_type == "seerr").all()
    if cached:
        return cached
    
    # Try to fetch from Seerr if server is configured
    server = db.query(ServerConfig).filter(
        ServerConfig.service_type == "seerr",
        ServerConfig.is_active == True
    ).first()
    
    if not server:
        raise HTTPException(status_code=400, detail="No Seerr server configured")
    
    try:
        client = SeerrClient(url=server.url, api_key=server.api_key)
        users = client.get_users()
        
        # Cache users in database
        for user in users:
            external_user = ExternalUser(
                service_type="seerr",
                external_id=str(user.get("id", "")),
                username=user.get("displayName", user.get("plexUsername", "")),
                email=user.get("email")
            )
            db.add(external_user)
        
        db.commit()
        
        # Return cached users
        return db.query(ExternalUser).filter(ExternalUser.service_type == "seerr").all()
        
    except Exception as e:
        logger.error(f"Failed to fetch Seerr users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Seerr users: {str(e)}")


@router.post("/sync")
async def sync_users(db: Session = Depends(get_db)):
    """Sync users from all configured services."""
    results = {"plex": None, "jellyfin": None, "seerr": None}
    
    # Sync Plex users
    plex_server = db.query(ServerConfig).filter(
        ServerConfig.service_type == "plex",
        ServerConfig.is_active == True
    ).first()
    
    if plex_server:
        try:
            client = PlexClient(token=plex_server.token, url=plex_server.url)
            users = client.get_users()
            
            # Clear existing cache
            db.query(ExternalUser).filter(ExternalUser.service_type == "plex").delete()
            
            # Cache new users
            for user in users:
                external_user = ExternalUser(
                    service_type="plex",
                    external_id=str(user.get("id", "")),
                    username=user.get("username", ""),
                    email=user.get("email")
                )
                db.add(external_user)
            
            results["plex"] = f"Synced {len(users)} users"
        except Exception as e:
            results["plex"] = f"Error: {str(e)}"
    
    # Sync Jellyfin users
    jellyfin_server = db.query(ServerConfig).filter(
        ServerConfig.service_type == "jellyfin",
        ServerConfig.is_active == True
    ).first()
    
    if jellyfin_server:
        try:
            client = JellyfinClient(url=jellyfin_server.url, api_key=jellyfin_server.api_key)
            users = client.get_users()
            
            # Clear existing cache
            db.query(ExternalUser).filter(ExternalUser.service_type == "jellyfin").delete()
            
            # Cache new users
            for user in users:
                external_user = ExternalUser(
                    service_type="jellyfin",
                    external_id=str(user.get("Id", "")),
                    username=user.get("Name", ""),
                    email=user.get("ConnectUserName")
                )
                db.add(external_user)
            
            results["jellyfin"] = f"Synced {len(users)} users"
        except Exception as e:
            results["jellyfin"] = f"Error: {str(e)}"
    
    # Sync Seerr users
    seerr_server = db.query(ServerConfig).filter(
        ServerConfig.service_type == "seerr",
        ServerConfig.is_active == True
    ).first()
    
    if seerr_server:
        try:
            client = SeerrClient(url=seerr_server.url, api_key=seerr_server.api_key)
            users = client.get_users()
            
            # Clear existing cache
            db.query(ExternalUser).filter(ExternalUser.service_type == "seerr").delete()
            
            # Cache new users
            for user in users:
                external_user = ExternalUser(
                    service_type="seerr",
                    external_id=str(user.get("id", "")),
                    username=user.get("displayName", user.get("plexUsername", "")),
                    email=user.get("email")
                )
                db.add(external_user)
            
            results["seerr"] = f"Synced {len(users)} users"
        except Exception as e:
            results["seerr"] = f"Error: {str(e)}"
    
    db.commit()
    logger.info("Synced users from all services")
    
    return {"success": True, "results": results}