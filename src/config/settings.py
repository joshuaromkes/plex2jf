"""Application settings management."""
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic_settings import BaseSettings

from src.config.models import Config


class Settings(BaseSettings):
    """Application settings."""
    # Config file path
    config_path: str = "/app/config.yaml"
    
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


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default path.
        
    Returns:
        Config: Parsed configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if config_path is None:
        config_path = get_settings().config_path
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
    
    return Config(**data)


def get_db_url() -> str:
    """Get database URL from settings."""
    settings = get_settings()
    return f"sqlite:///{settings.db_path}"