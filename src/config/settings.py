"""Application settings management."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    # Database
    db_path: str = "/data/plex2jf.db"
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "/data/plex2jf.log"
    
    # Polling
    polling_interval: int = 300
    
    class Config:
        env_prefix = "PLEX2JF_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_db_url() -> str:
    """Get database URL from settings."""
    settings = get_settings()
    return f"sqlite:///{settings.db_path}"