"""Configuration management for Plex2JF."""

import logging
import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

from .models.user_mapping import UserMapping, UserMappings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Plex settings
    plex_url: str = Field(default="http://localhost:32400", description="Plex server URL")
    plex_token: str = Field(default="", description="Plex token")
    
    # Jellyfin settings
    jellyfin_url: str = Field(default="http://localhost:8096", description="Jellyfin server URL")
    jellyfin_api_key: str = Field(default="", description="Jellyfin API key")
    
    # Seerr settings
    seerr_url: str = Field(default="http://localhost:5055", description="Seerr server URL")
    seerr_api_key: str = Field(default="", description="Seerr API key")
    
    # Sync settings
    sync_interval_minutes: int = Field(default=5, description="Sync interval in minutes")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Paths
    config_dir: Path = Field(default=Path("/app/config"), description="Configuration directory")
    data_dir: Path = Field(default=Path("/app/data"), description="Data directory for state")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_user_mappings(config_path: Path) -> UserMappings:
    """Load user mappings from YAML configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        UserMappings object
    """
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return UserMappings()
    
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data or 'user_mappings' not in data:
            logger.warning("No user_mappings found in config file")
            return UserMappings()
        
        mappings = []
        for mapping_data in data['user_mappings']:
            try:
                mapping = UserMapping(**mapping_data)
                mappings.append(mapping)
                logger.info(f"Loaded user mapping: {mapping}")
            except Exception as e:
                logger.error(f"Failed to parse user mapping: {e}")
        
        return UserMappings(mappings=mappings)
        
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return UserMappings()


def create_default_config(config_path: Path) -> None:
    """Create a default configuration file.
    
    Args:
        config_path: Path where the config file should be created
    """
    default_config = """# Plex2JF Configuration
# Map users across Plex, Jellyfin, and Seerr

user_mappings:
  # Example mapping - replace with your actual users
  - plex_username: "john_doe"
    jellyfin_username: "john_doe"
    seerr_username: "john_doe"
  
  # Add more mappings as needed
  # - plex_username: "jane_doe"
  #   jellyfin_username: "jane_doe"
  #   seerr_username: "jane_doe"
"""
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        f.write(default_config)
    
    logger.info(f"Created default config file: {config_path}")


def validate_settings(settings: Settings) -> List[str]:
    """Validate application settings.
    
    Args:
        settings: Application settings
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not settings.plex_token:
        errors.append("PLEX_TOKEN is required")
    
    if not settings.jellyfin_api_key:
        errors.append("JELLYFIN_API_KEY is required")
    
    if not settings.seerr_api_key:
        errors.append("SEERR_API_KEY is required")
    
    return errors


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
