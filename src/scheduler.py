"""Background scheduler for polling tasks."""
import logging
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config.settings import load_config, get_settings
from src.database.session import init_db, get_db_context
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.services.sync_engine import SyncEngine
from src.services.poller import PollerService
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def run_polling_job():
    """Run the polling job."""
    logger.info("Running scheduled polling job...")
    
    try:
        config = load_config()
        
        with get_db_context() as db:
            # Initialize API clients
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
            
            # Create sync engine
            sync_engine = SyncEngine(db, plex_client, jellyfin_client, seerr_client, config)
            
            # Create poller
            poller = PollerService(db, plex_client, sync_engine)
            
            # Poll Plex watchlists
            if config.sync.features.plex_watchlist_to_seerr or config.sync.features.plex_watchlist_to_jellyfin:
                poller.poll_plex_watchlists()
            
            # Retry pending items
            sync_engine.retry_pending_items()
            
    except Exception as e:
        logger.error(f"Error in polling job: {e}")


def main():
    """Main entry point for scheduler."""
    # Load config
    config = load_config()
    
    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
    )
    
    # Initialize database
    init_db()
    
    logger.info("Starting plex2jf scheduler...")
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Add polling job
    scheduler.add_job(
        run_polling_job,
        trigger=IntervalTrigger(seconds=config.sync.polling_interval),
        id='plex_poll',
        name='Plex Watchlist Poll',
        replace_existing=True,
    )
    
    # Start scheduler
    scheduler.start()
    
    logger.info(f"Scheduler started. Polling interval: {config.sync.polling_interval} seconds")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
