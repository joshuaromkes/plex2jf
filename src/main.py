"""Main FastAPI application."""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config.settings import load_config, get_settings
from src.config.db_config import (
    get_log_level, get_log_file,
    get_server_credentials, get_feature_flags,
)
from src.database.session import init_db, get_db, get_db_context
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.services.sync_engine import SyncEngine
from src.services.poller import PollerService
from src.services.user_mapper import UserMapper
from src.webhooks.routes import router as webhooks_router
from src.utils.logging_config import setup_logging
from src._version import __version__

# Import new routes
from src.routes import (
    servers_router,
    users_router,
    settings_router,
    dashboard_router,
    system_router,
)

logger = logging.getLogger(__name__)

# Path to frontend build directory
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting plex2jf...")

    # Initialize database
    init_db()

    # Configure logging from DB settings (falling back to defaults).
    # config.yaml is no longer required — everything is DB-managed.
    try:
        with get_db_context() as db:
            level = get_log_level(db)
            log_file_path = get_log_file(db)
    except Exception:
        level = "INFO"
        log_file_path = "/data/plex2jf.log"

    setup_logging(level=level, log_file=log_file_path or "/data/plex2jf.log")

    # Optionally sync user_mappings from config.yaml if it exists (legacy bridge).
    # On a fresh install without config.yaml this is silently skipped.
    try:
        config = load_config()
        with get_db_context() as db:
            user_mapper = UserMapper(db)
            user_mapper.sync_user_mappings(config.user_mappings)
            logger.info(f"Synced {len(config.user_mappings)} user mappings from config.yaml")
    except FileNotFoundError:
        logger.info("No config.yaml found — skipping legacy user-mapping import.")
    except Exception as e:
        logger.warning(f"Could not sync legacy user mappings: {e}")

    logger.info("plex2jf started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down plex2jf...")


# Create FastAPI app
app = FastAPI(
    title="plex2jf",
    description="Sync media requests and favorites between Plex, Jellyfin, and Seerr",
    version=__version__,
    lifespan=lifespan,
)

# Include routers
app.include_router(webhooks_router)
app.include_router(servers_router)
app.include_router(users_router)
app.include_router(settings_router)
app.include_router(dashboard_router)
app.include_router(system_router)


def get_sync_engine(db: Session = Depends(get_db)) -> SyncEngine | None:
    """Get sync engine instance using DB-stored server credentials.

    Returns None if any required server is not configured (so callers
    can return a friendly error instead of crashing).
    """
    plex = get_server_credentials(db, "plex")
    jellyfin = get_server_credentials(db, "jellyfin")
    seerr = get_server_credentials(db, "seerr")

    if not plex:
        logger.warning("No active Plex server configured — sync engine unavailable")
        return None

    plex_client = PlexClient(token=plex["token"], url=plex["url"])
    jellyfin_client = JellyfinClient(
        url=jellyfin["url"], api_key=jellyfin["api_key"]
    ) if jellyfin else None
    seerr_client = SeerrClient(
        url=seerr["url"], api_key=seerr["api_key"]
    ) if seerr else None

    flags = get_feature_flags(db)
    # Build a minimal config-like object for SyncEngine compatibility
    class _Cfg:
        sync = type("s", (), {"features": type("f", (), flags)})()
    return SyncEngine(db, plex_client, jellyfin_client, seerr_client, _Cfg())


@app.get("/api")
async def api_root() -> dict:
    """API root endpoint showing available endpoints."""
    return {
        "service": "plex2jf",
        "version": __version__,
        "description": "Sync media requests and favorites between Plex, Jellyfin, and Seerr",
        "api_endpoints": {
            "servers": "/api/servers",
            "users": "/api/users",
            "settings": "/api/settings",
            "dashboard": "/api/dashboard",
            "system": "/api/system",
            "health": "/api/system/health",
            "webhooks": {
                "seerr": "/webhooks/seerr",
                "health": "/webhooks/health"
            },
            "legacy_sync": {
                "plex-watchlist": "/sync/plex-watchlist",
                "retry-pending": "/sync/retry-pending"
            }
        }
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)) -> dict:
    """Health check endpoint."""
    try:
        # Check database
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "service": "plex2jf",
    }


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)) -> dict:
    """Get sync statistics (DB-only, no API clients needed)."""
    se = get_sync_engine(db)
    if se is None:
        return {"total_items": 0, "synced_to_jellyfin": 0, "synced_to_seerr": 0,
                "pending": 0, "seerr_request": {"total": 0, "synced": 0, "pending": 0, "failed": 0}}
    return se.get_stats()


@app.post("/sync/plex-watchlist")
async def sync_plex_watchlist(
    db: Session = Depends(get_db),
) -> dict:
    """Manually trigger Plex watchlist sync."""
    plex = get_server_credentials(db, "plex")
    if not plex:
        raise HTTPException(
            status_code=503,
            detail="No Plex server configured. Add one in Settings → Servers.",
        )
    se = get_sync_engine(db)
    if se is None:
        raise HTTPException(status_code=503, detail="Sync engine unavailable.")
    plex_client = PlexClient(token=plex["token"], url=plex["url"])
    poller = PollerService(db, plex_client, se)
    try:
        count = poller.poll_plex_watchlists()
        return {"status": "success", "synced_items": count}
    except Exception as e:
        logger.error(f"Error syncing Plex watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/retry-pending")
async def retry_pending(
    db: Session = Depends(get_db),
) -> dict:
    """Retry pending items."""
    se = get_sync_engine(db)
    if se is None:
        raise HTTPException(
            status_code=503,
            detail="No Plex server configured. Add one in Settings → Servers.",
        )
    try:
        count = se.retry_pending_items()
        return {"status": "success", "retried_items": count}
    except Exception as e:
        logger.error(f"Error retrying pending items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve frontend static files (if built)
if os.path.exists(FRONTEND_DIR):
    # Mount static files
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend for all non-API routes."""
        # Don't serve frontend for API routes
        if full_path.startswith("api/") or full_path.startswith("webhooks/"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for all routes (React Router handles routing)
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")
else:
    @app.get("/")
    async def root() -> dict:
        """Root endpoint when frontend is not built."""
        return {
            "service": "plex2jf",
            "version": __version__,
            "description": "Sync media requests and favorites between Plex, Jellyfin, and Seerr",
            "frontend": "Not built - API only mode",
            "endpoints": {
                "api": "/api",
                "health": "/health",
                "docs": "/docs",
            }
        }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )