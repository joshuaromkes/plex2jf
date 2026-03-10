"""Main entry point for Plex2JF sync application."""

import logging
import signal
import sys
import time
from pathlib import Path

import schedule

from .config import (
    Settings,
    load_user_mappings,
    create_default_config,
    validate_settings,
    setup_logging
)
from .api_clients.plex_client import PlexClient
from .api_clients.jellyfin_client import JellyfinClient
from .api_clients.seerr_client import SeerrClient
from .sync_engine import SyncEngine

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Received shutdown signal, stopping...")
    running = False


def run_sync_job(sync_engine: SyncEngine) -> None:
    """Run a single sync job."""
    try:
        results = sync_engine.run_sync()
        logger.info(f"Sync completed: {results}")
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)


def main():
    """Main application entry point."""
    global running
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load settings
    settings = Settings()
    
    # Set up logging
    setup_logging(settings.log_level)
    
    logger.info("=" * 50)
    logger.info("Plex2JF Starting")
    logger.info("=" * 50)
    
    # Validate settings
    errors = validate_settings(settings)
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    # Load user mappings
    config_path = settings.config_dir / "config.yaml"
    if not config_path.exists():
        logger.info("Config file not found, creating default...")
        create_default_config(config_path)
        logger.warning(f"Please edit {config_path} to add your user mappings")
    
    user_mappings = load_user_mappings(config_path)
    
    if not user_mappings.mappings:
        logger.error("No user mappings configured. Please add mappings to the config file.")
        sys.exit(1)
    
    logger.info(f"Loaded {len(user_mappings.mappings)} user mappings")
    
    # Initialize API clients
    logger.info("Initializing API clients...")
    
    plex_client = PlexClient(
        base_url=settings.plex_url,
        token=settings.plex_token
    )
    
    jellyfin_client = JellyfinClient(
        base_url=settings.jellyfin_url,
        api_key=settings.jellyfin_api_key
    )
    
    seerr_client = SeerrClient(
        base_url=settings.seerr_url,
        api_key=settings.seerr_api_key
    )
    
    # Check health of all services
    logger.info("Checking service health...")
    health = {
        'plex': plex_client.health_check(),
        'jellyfin': jellyfin_client.health_check(),
        'seerr': seerr_client.health_check()
    }
    
    for service, status in health.items():
        status_str = "✓ OK" if status else "✗ FAILED"
        logger.info(f"  {service.capitalize()}: {status_str}")
    
    if not all(health.values()):
        logger.error("Some services are unavailable. Please check your configuration.")
        # Continue anyway, as services might come back online
    
    # Initialize sync engine
    state_file = settings.data_dir / "sync_state.json"
    sync_engine = SyncEngine(
        plex_client=plex_client,
        jellyfin_client=jellyfin_client,
        seerr_client=seerr_client,
        user_mappings=user_mappings,
        state_file=state_file
    )
    
    # Schedule sync job
    interval = settings.sync_interval_minutes
    logger.info(f"Scheduling sync every {interval} minutes")
    
    # Run initial sync
    logger.info("Running initial sync...")
    run_sync_job(sync_engine)
    
    # Schedule recurring sync
    schedule.every(interval).minutes.do(run_sync_job, sync_engine)
    
    # Main loop
    logger.info("Entering main loop (press Ctrl+C to stop)")
    
    while running:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(5)
    
    logger.info("Plex2JF stopped")
    return 0


def run_once():
    """Run a single sync and exit (useful for testing/cron)."""
    # Load settings
    settings = Settings()
    
    # Set up logging
    setup_logging(settings.log_level)
    
    logger.info("Plex2JF - Single Run Mode")
    
    # Validate settings
    errors = validate_settings(settings)
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1
    
    # Load user mappings
    config_path = settings.config_dir / "config.yaml"
    user_mappings = load_user_mappings(config_path)
    
    if not user_mappings.mappings:
        logger.error("No user mappings configured.")
        return 1
    
    # Initialize API clients
    plex_client = PlexClient(
        base_url=settings.plex_url,
        token=settings.plex_token
    )
    
    jellyfin_client = JellyfinClient(
        base_url=settings.jellyfin_url,
        api_key=settings.jellyfin_api_key
    )
    
    seerr_client = SeerrClient(
        base_url=settings.seerr_url,
        api_key=settings.seerr_api_key
    )
    
    # Initialize sync engine
    state_file = settings.data_dir / "sync_state.json"
    sync_engine = SyncEngine(
        plex_client=plex_client,
        jellyfin_client=jellyfin_client,
        seerr_client=seerr_client,
        user_mappings=user_mappings,
        state_file=state_file
    )
    
    # Run sync
    results = sync_engine.run_sync()
    logger.info(f"Sync results: {results}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
