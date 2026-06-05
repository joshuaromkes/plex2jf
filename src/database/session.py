"""Database session management."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import get_db_url

# Global engine instance
engine = None
SessionLocal = None


def init_db() -> None:
    """Initialize database engine and create tables."""
    global engine, SessionLocal
    
    db_url = get_db_url()
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    from src.database.models import Base
    Base.metadata.create_all(bind=engine)

    # ── v1.2.0 migration: make sync_state.user_mapping_id nullable ──
    _migrate_v1_2_0(engine)


def _migrate_v1_2_0(engine) -> None:
    """Make sync_state.user_mapping_id nullable (v1.2.0).

    SQLite does not support ALTER COLUMN, so the table is recreated.
    Only runs if the column is still NOT NULL.
    """
    import logging
    from sqlalchemy import inspect, text

    logger = logging.getLogger(__name__)
    inspector = inspect(engine)

    if "sync_state" not in inspector.get_table_names():
        return  # fresh install — create_all already used the new schema

    columns = {c["name"]: c for c in inspector.get_columns("sync_state")}
    col = columns.get("user_mapping_id")
    if col is None or not col.get("nullable", True):
        # Already nullable (new schema) or column missing — nothing to do.
        return

    logger.info("Migrating sync_state.user_mapping_id to nullable…")
    with engine.connect() as conn:
        # 1. Create new table with the nullable column
        conn.execute(text("""
            CREATE TABLE sync_state_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_mapping_id INTEGER REFERENCES user_mappings(id),
                media_type VARCHAR NOT NULL,
                external_id VARCHAR NOT NULL,
                title VARCHAR,
                source VARCHAR NOT NULL,
                source_id VARCHAR,
                synced_to_jellyfin BOOLEAN DEFAULT 0,
                jellyfin_item_id VARCHAR,
                synced_to_seerr BOOLEAN DEFAULT 0,
                seerr_request_id VARCHAR,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                first_seen_at DATETIME,
                last_synced_at DATETIME,
                UNIQUE(user_mapping_id, external_id, source)
            )
        """))
        # 2. Copy existing rows
        conn.execute(text("""
            INSERT INTO sync_state_new SELECT * FROM sync_state
        """))
        # 3. Swap tables
        conn.execute(text("DROP TABLE sync_state"))
        conn.execute(text("ALTER TABLE sync_state_new RENAME TO sync_state"))
        conn.commit()

    logger.info("Migration v1.2.0 complete.")


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()