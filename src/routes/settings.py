"""Settings API routes."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import AppSettings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

# Default settings
DEFAULT_SETTINGS = {
    "sync_plex_watchlist": True,
    "sync_seerr_requests": True,
    "polling_interval": 300,
    "webhook_enabled": True,
    "log_level": "INFO",
}


class SettingValue(BaseModel):
    """Schema for a single setting value."""
    key: str
    value: Any


class SettingsBulkUpdate(BaseModel):
    """Schema for bulk settings update."""
    settings: Dict[str, Any]


class SettingsResponse(BaseModel):
    """Schema for settings response."""
    success: bool
    data: Dict[str, Any]


def get_setting(db: Session, key: str) -> Optional[AppSettings]:
    """Get a single setting from database."""
    return db.query(AppSettings).filter(AppSettings.key == key).first()


def get_setting_value(db: Session, key: str, default: Any = None) -> Any:
    """Get a setting value, returning default if not found."""
    setting = get_setting(db, key)
    if setting:
        try:
            return json.loads(setting.value)
        except json.JSONDecodeError:
            return setting.value
    return default


def set_setting(db: Session, key: str, value: Any) -> AppSettings:
    """Set a setting value in database."""
    setting = get_setting(db, key)
    
    if isinstance(value, (dict, list, bool, int, float)):
        value = json.dumps(value)
    
    if setting:
        setting.value = value
        setting.updated_at = datetime.now(timezone.utc)
    else:
        setting = AppSettings(key=key, value=value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return setting


@router.get("", response_model=SettingsResponse)
async def get_all_settings(db: Session = Depends(get_db)):
    """Get all application settings."""
    settings = db.query(AppSettings).all()
    
    # Build settings dict
    result = DEFAULT_SETTINGS.copy()
    for setting in settings:
        try:
            result[setting.key] = json.loads(setting.value)
        except json.JSONDecodeError:
            result[setting.key] = setting.value
    
    return SettingsResponse(success=True, data=result)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    update: SettingsBulkUpdate,
    db: Session = Depends(get_db)
):
    """Update multiple settings at once."""
    for key, value in update.settings.items():
        set_setting(db, key, value)
        logger.info(f"Updated setting: {key}")
    
    # Return updated settings
    settings = db.query(AppSettings).all()
    result = DEFAULT_SETTINGS.copy()
    for setting in settings:
        try:
            result[setting.key] = json.loads(setting.value)
        except json.JSONDecodeError:
            result[setting.key] = setting.value
    
    return SettingsResponse(success=True, data=result)


@router.get("/{key}")
async def get_setting_by_key(key: str, db: Session = Depends(get_db)):
    """Get a specific setting by key."""
    value = get_setting_value(db, key, DEFAULT_SETTINGS.get(key))
    
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    
    return {"success": True, "key": key, "value": value}


@router.put("/{key}")
async def update_setting_by_key(
    key: str,
    value: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update a specific setting by key."""
    if "value" not in value:
        raise HTTPException(status_code=400, detail="Request body must contain 'value' field")
    
    setting = set_setting(db, key, value["value"])
    logger.info(f"Updated setting: {key}")
    
    try:
        parsed_value = json.loads(setting.value)
    except json.JSONDecodeError:
        parsed_value = setting.value
    
    return {"success": True, "key": key, "value": parsed_value}