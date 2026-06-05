"""User mapping service."""
import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from src.database.models import UserMapping as UserMappingModel
from src.config.models import UserMapping

logger = logging.getLogger(__name__)


class UserMapper:
    """Service for mapping users between Plex, Jellyfin, and Seerr."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_user_mappings(self, mappings: List[UserMapping]) -> None:
        """Sync user mappings from config to database.
        
        Args:
            mappings: List of user mappings from config
        """
        for mapping in mappings:
            # Skip example/placeholder mappings
            if self._is_example_mapping(mapping):
                logger.debug(f"Skipping example mapping for {mapping.plex_username}")
                continue
            
            # Check if mapping exists
            existing = (
                self.db.query(UserMappingModel)
                .filter(UserMappingModel.plex_username == mapping.plex_username)
                .first()
            )
            
            if existing:
                # Update existing
                existing.plex_user_id = mapping.plex_user_id
                existing.jellyfin_user_id = mapping.jellyfin_user_id
                existing.seerr_user_id = mapping.seerr_user_id
                logger.debug(f"Updated user mapping for {mapping.plex_username}")
            else:
                # Create new
                new_mapping = UserMappingModel(
                    plex_username=mapping.plex_username,
                    plex_user_id=mapping.plex_user_id,
                    jellyfin_user_id=mapping.jellyfin_user_id,
                    seerr_user_id=mapping.seerr_user_id,
                )
                self.db.add(new_mapping)
                logger.info(f"Created user mapping for {mapping.plex_username}")
        
        self.db.commit()
    
    def _is_example_mapping(self, mapping: UserMapping) -> bool:
        """Check if a mapping looks like an example/placeholder.
        
        Args:
            mapping: User mapping to check
            
        Returns:
            True if mapping appears to be an example
        """
        # Default example usernames that look like placeholders
        example_usernames = {"john_plex", "jane_plex", "john", "jane"}
        if mapping.plex_username in example_usernames:
            return True
        
        # Common placeholder IDs
        placeholder_ids = {"abc123", "def456", "12345678", "87654321"}
        if mapping.jellyfin_user_id in placeholder_ids:
            return True
        if mapping.seerr_user_id in {"1", "2"}:
            return True
        
        return False
    
    def get_mapping_by_plex_username(self, plex_username: str) -> Optional[UserMappingModel]:
        """Get user mapping by Plex username.
        
        Uses case-insensitive and whitespace-tolerant matching since Plex
        usernames from GraphQL may differ from stored usernames.
        
        Args:
            plex_username: Plex username
            
        Returns:
            User mapping if found, None otherwise
        """
        # Normalize the search username
        normalized_search = plex_username.lower().replace(' ', '')
        
        # Get all active mappings and check normalized match
        all_mappings = self.db.query(UserMappingModel).filter(UserMappingModel.is_active == True).all()
        
        for mapping in all_mappings:
            normalized_stored = mapping.plex_username.lower().replace(' ', '')
            if normalized_stored == normalized_search:
                return mapping
        
        return None
    
    def get_mapping_by_seerr_user_id(self, seerr_user_id: str) -> Optional[UserMappingModel]:
        """Get user mapping by Seerr user ID.
        
        Args:
            seerr_user_id: Seerr user ID
            
        Returns:
            User mapping if found, None otherwise
        """
        return (
            self.db.query(UserMappingModel)
            .filter(UserMappingModel.seerr_user_id == seerr_user_id)
            .first()
        )
    
    def get_all_mappings(self) -> List[UserMappingModel]:
        """Get all user mappings.
        
        Returns:
            List of user mappings
        """
        return self.db.query(UserMappingModel).all()
    
    def auto_match_users(
        self,
        plex_users: List[Dict[str, Any]],
        jellyfin_users: List[Dict[str, Any]],
        seerr_users: List[Dict[str, Any]],
    ) -> List[UserMapping]:
        """Attempt to auto-match users across services.
        
        Args:
            plex_users: List of Plex users
            jellyfin_users: List of Jellyfin users
            seerr_users: List of Seerr users
            
        Returns:
            List of suggested user mappings
        """
        suggestions = []
        
        for plex_user in plex_users:
            plex_username = plex_user.get('title', '')
            plex_id = plex_user.get('id')
            
            # Try exact match on username
            jf_match = next(
                (u for u in jellyfin_users if u.get('Name') == plex_username),
                None
            )
            seerr_match = next(
                (u for u in seerr_users if u.get('username') == plex_username),
                None
            )
            
            if jf_match and seerr_match:
                suggestions.append(UserMapping(
                    plex_username=plex_username,
                    plex_user_id=str(plex_id) if plex_id else None,
                    jellyfin_user_id=jf_match.get('Id'),
                    seerr_user_id=str(seerr_match.get('id')),
                ))
                logger.info(f"Auto-matched user: {plex_username}")
        
        return suggestions