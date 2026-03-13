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
from src.database.session import init_db, get_db
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.services.sync_engine import SyncEngine
from src.services.poller import PollerService
from src.services.user_mapper import UserMapper
from src.webhooks.routes import router as webhooks_router
from src.utils.logging_config import setup_logging

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
    
    # Load config and sync user mappings
    try:
        config = load_config()
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
        )
        
        # Sync user mappings to database
        from src.database.session import get_db_context
        with get_db_context() as db:
            user_mapper = UserMapper(db)
            user_mapper.sync_user_mappings(config.user_mappings)
            logger.info(f"Synced {len(config.user_mappings)} user mappings")
    
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    logger.info("plex2jf started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down plex2jf...")


# Create FastAPI app
app = FastAPI(
    title="plex2jf",
    description="Sync media requests and favorites between Plex, Jellyfin, and Seerr",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(webhooks_router)
app.include_router(servers_router)
app.include_router(users_router)
app.include_router(settings_router)
app.include_router(dashboard_router)
app.include_router(system_router)


def get_sync_engine(db: Session = Depends(get_db)) -> SyncEngine:
    """Get sync engine instance."""
    config = load_config()
    
    plex_client = PlexClient(
        token=config.plex.token,
        url=config.plex.url,
    )
    jellyfin_client = JellyfinClient(
        url=config.jellyfin.url,
        api_key=config.jellyfin.api_key,
    )
    seerr_client = SeerrClient(
        url=config.seerr.url,
        api_key=config.seerr.api_key,
    )
    
    return SyncEngine(db, plex_client, jellyfin_client, seerr_client, config)


@app.get("/api")
async def api_root() -> dict:
    """API root endpoint showing available endpoints."""
    return {
        "service": "plex2jf",
        "version": "1.0.0",
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
async def get_stats(sync_engine: SyncEngine = Depends(get_sync_engine)) -> dict:
    """Get sync statistics."""
    return sync_engine.get_stats()


@app.post("/sync/plex-watchlist")
async def sync_plex_watchlist(
    sync_engine: SyncEngine = Depends(get_sync_engine),
    poller: PollerService = Depends(lambda db: PollerService(db, PlexClient(
        token=load_config().plex.token,
        url=load_config().plex.url,
    ), sync_engine)),
) -> dict:
    """Manually trigger Plex watchlist sync."""
    try:
        count = poller.poll_plex_watchlists()
        return {"status": "success", "synced_items": count}
    except Exception as e:
        logger.error(f"Error syncing Plex watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/retry-pending")
async def retry_pending(
    sync_engine: SyncEngine = Depends(get_sync_engine),
) -> dict:
    """Retry pending items."""
    try:
        count = sync_engine.retry_pending_items()
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
            "version": "1.0.0",
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
        port=settings.polling_interval if hasattr(settings, 'webhook_port') else 8000,
        reload=False,
    )