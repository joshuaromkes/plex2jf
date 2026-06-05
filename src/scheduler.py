"""Background scheduler for polling tasks."""
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config.db_config import (
    get_log_level, get_log_file,
    get_server_credentials, get_feature_flags, get_polling_interval,
)
from src.database.session import init_db, get_db_context
from src.api.plex import PlexClient
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.services.sync_engine import SyncEngine
from src.services.poller import PollerService
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Module-level reference to the scheduler, so run_polling_job() can
# reschedule itself when the DB-configured polling interval changes.
_scheduler = None


def run_polling_job():
    """Run the polling job."""
    logger.info("Running scheduled polling job...")

    try:
        with get_db_context() as db:
            # Build API clients from DB-stored server credentials
            plex = get_server_credentials(db, "plex")
            jellyfin = get_server_credentials(db, "jellyfin")
            seerr = get_server_credentials(db, "seerr")

            if not plex:
                logger.warning("No active Plex server — skipping poll")
                return

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

            sync_engine = SyncEngine(db, plex_client, jellyfin_client, seerr_client, _Cfg())
            poller = PollerService(db, plex_client, sync_engine)

            # Poll Plex watchlists
            if flags.get("plex_watchlist_to_seerr") or flags.get("plex_watchlist_to_jellyfin"):
                poller.poll_plex_watchlists()

            # Poll Seerr requests -> Jellyfin favorites (unmapped always included)
            if flags.get("seerr_to_jellyfin"):
                poller.poll_seerr_requests_to_jellyfin(
                    include_unmapped=True,
                )

            # Retry pending items
            sync_engine.retry_pending_items()

    except Exception as e:
        logger.error(f"Error in polling job: {e}")

    # After every poll, check whether the DB-configured interval has
    # changed (e.g. the user edited it in the Settings UI).  Reschedule
    # the job if it has.
    try:
        with get_db_context() as db:
            db_interval = get_polling_interval(db)
        _reschedule_if_changed(db_interval)
    except Exception:
        pass


def _reschedule_if_changed(db_interval):
    """Reschedule the plex_poll job if the interval has changed."""
    if db_interval is None or _scheduler is None:
        return
    job = _scheduler.get_job('plex_poll')
    if job is None:
        return
    current = int(job.trigger.interval.total_seconds())
    if current != db_interval:
        logger.info(
            "Rescheduling poll job: %ds -> %ds (from DB settings)",
            current, db_interval,
        )
        _scheduler.reschedule_job(
            'plex_poll',
            trigger=IntervalTrigger(seconds=db_interval),
        )


def main():
    """Main entry point for scheduler."""
    # Initialize database
    init_db()

    # Read logging config from DB (fall back to defaults)
    with get_db_context() as db:
        level = get_log_level(db)
        log_file_path = get_log_file(db)

    setup_logging(
        level=level,
        log_file=log_file_path or "/data/plex2jf.log",
    )

    logger.info("Starting plex2jf scheduler...")

    # Determine polling interval from DB (UI Settings page is authoritative).
    with get_db_context() as db:
        interval = get_polling_interval(db)

    # Create scheduler
    global _scheduler
    _scheduler = BackgroundScheduler()

    # Add polling job
    _scheduler.add_job(
        run_polling_job,
        trigger=IntervalTrigger(seconds=interval),
        id='plex_poll',
        name='Plex Watchlist Poll',
        replace_existing=True,
    )

    # Start scheduler
    _scheduler.start()

    logger.info(f"Scheduler started. Polling interval: {interval} seconds")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        _scheduler.shutdown()


if __name__ == "__main__":
    main()
