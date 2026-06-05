"""
Database-backed configuration access.

Replaces the original config.yaml dependency.  All settings and
server credentials are read from the database (ServerConfig and
AppSettings tables) so config.yaml is no longer required at startup.
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import ServerConfig, AppSettings

logger = logging.getLogger(__name__)

# ── default values (match config.example.yaml / Settings.DEFAULT_SETTINGS) ──

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "/data/plex2jf.log"
DEFAULT_POLLING_INTERVAL = 300

DEFAULT_FEATURES = {
    "seerr_to_jellyfin": True,
    "plex_watchlist_to_seerr": True,
    "plex_watchlist_to_jellyfin": True,
    # When enabled, Seerr users without a UserMapping row are still synced
    # to Jellyfin by matching usernames between the two services.
    "sync_unmapped_seerr": False,
}


def get_setting(db: Session, key: str, default=None):
    """Return a single setting value from app_settings, falling back to *default*."""
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row is None:
        return default
    try:
        return json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return row.value


def get_log_level(db: Session) -> str:
    return get_setting(db, "log_level", DEFAULT_LOG_LEVEL)


def get_log_file(db: Session) -> str | None:
    return get_setting(db, "log_file", DEFAULT_LOG_FILE)


def get_polling_interval(db: Session) -> int:
    return int(get_setting(db, "polling_interval", DEFAULT_POLLING_INTERVAL))


def get_feature_flags(db: Session) -> dict:
    """Return feature-flag dict with all three sync flags.

    Falls back to DEFAULT_FEATURES when no DB settings exist (first run).
    Individual flags can be overridden via 'feature_<name>' AppSettings rows.
    """
    flags = DEFAULT_FEATURES.copy()
    for flag_name in DEFAULT_FEATURES:
        db_key = f"feature_{flag_name}"
        raw = get_setting(db, db_key, None)
        if raw is not None:
            flags[flag_name] = bool(raw)
    return flags


def get_server_credentials(
    db: Session, service_type: str
) -> dict | None:
    """Return {url, token, api_key, is_active} for an active server, or None."""
    server = (
        db.query(ServerConfig)
        .filter(
            ServerConfig.service_type == service_type,
            ServerConfig.is_active == True,
        )
        .first()
    )
    if server is None:
        return None
    return {
        "url": server.url,
        "token": server.token,
        "api_key": server.api_key,
        "is_active": server.is_active,
    }
