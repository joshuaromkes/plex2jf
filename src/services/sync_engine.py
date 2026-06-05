"""Sync engine for coordinating sync operations."""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Set, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.api.plex import PlexClient, PlexWatchlistItem
from src.api.jellyfin import JellyfinClient
from src.api.seerr import SeerrClient
from src.database.models import SyncState, UserMapping, PollingState
from src.services.user_mapper import UserMapper

logger = logging.getLogger(__name__)


class SyncEngine:
    """Core sync engine for coordinating sync operations."""
    
    def __init__(
        self,
        db: Session,
        plex_client: PlexClient,
        jellyfin_client: "JellyfinClient | None" = None,
        seerr_client: "SeerrClient | None" = None,
        config=None,
    ):
        self.db = db
        self.plex = plex_client
        self.jellyfin = jellyfin_client
        self.seerr = seerr_client
        self.user_mapper = UserMapper(db)
        self.config = config

    @staticmethod
    def _normalize_title_for_match(value: str) -> str:
        """Normalize title strings for loose matching."""
        lowered = str(value or '').strip().lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
        collapsed = re.sub(r"\s+", " ", cleaned).strip()
        return collapsed

    @staticmethod
    def _extract_year_from_value(value: Any) -> Optional[int]:
        """Best-effort year extraction from an int/string/date-like value."""
        if value is None:
            return None

        if isinstance(value, int):
            return value if 1800 <= value <= 2500 else None

        text = str(value).strip()
        match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b", text)
        if not match:
            return None

        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_tmdb_id(value: Any) -> Optional[str]:
        """Normalize TMDB ID to numeric string when possible."""
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        return text if text.isdigit() else None

    def _extract_candidate_tmdb_id(self, candidate: Dict[str, Any]) -> Optional[str]:
        """Extract TMDB ID from a Seerr search candidate payload."""
        media = candidate.get('media', {}) if isinstance(candidate, dict) else {}
        raw_value = (
            media.get('tmdbId')
            or candidate.get('tmdbId')
            or candidate.get('id')
        )

        if raw_value is None:
            return None

        try:
            return str(int(raw_value))
        except (TypeError, ValueError):
            return None

    def _score_search_candidate(
        self,
        candidate: Dict[str, Any],
        *,
        title: str,
        media_type: str,
        year: Optional[int],
        imdb_id: Optional[str],
        tvdb_id: Optional[str],
    ) -> Tuple[int, str]:
        """Score a Seerr search candidate for loose mapping confidence."""
        media = candidate.get('media', {}) if isinstance(candidate, dict) else {}

        candidate_type = str(
            candidate.get('mediaType')
            or media.get('mediaType')
            or candidate.get('type')
            or ''
        ).strip().lower()

        candidate_title = str(
            candidate.get('title')
            or candidate.get('name')
            or media.get('title')
            or media.get('name')
            or ''
        )

        candidate_year = self._extract_year_from_value(
            candidate.get('year')
            or media.get('year')
            or candidate.get('releaseDate')
            or candidate.get('firstAirDate')
            or media.get('releaseDate')
            or media.get('firstAirDate')
        )

        candidate_imdb = str(
            candidate.get('imdbId')
            or media.get('imdbId')
            or ''
        ).strip()
        candidate_tvdb = str(
            candidate.get('tvdbId')
            or media.get('tvdbId')
            or ''
        ).strip()

        wanted_title = self._normalize_title_for_match(title)
        got_title = self._normalize_title_for_match(candidate_title)

        score = 0
        reasons: List[str] = []

        # Strict external-ID evidence gets strongest weight.
        if imdb_id and candidate_imdb and imdb_id == candidate_imdb:
            score += 100
            reasons.append('imdb_match')
        if tvdb_id and candidate_tvdb and str(tvdb_id) == str(candidate_tvdb):
            score += 100
            reasons.append('tvdb_match')

        # Type agreement.
        if candidate_type in ('movie', 'tv'):
            if candidate_type == media_type:
                score += 25
                reasons.append('type_match')
            else:
                score -= 35
                reasons.append('type_mismatch')

        # Title agreement.
        if wanted_title and got_title:
            if wanted_title == got_title:
                score += 55
                reasons.append('title_exact')
            elif wanted_title in got_title or got_title in wanted_title:
                score += 40
                reasons.append('title_contains')
            else:
                wanted_tokens = set(wanted_title.split())
                got_tokens = set(got_title.split())
                overlap = len(wanted_tokens.intersection(got_tokens))
                if overlap > 0:
                    ratio = overlap / max(len(wanted_tokens), len(got_tokens))
                    token_score = int(ratio * 30)
                    score += token_score
                    reasons.append(f'title_tokens_{token_score}')

        # Year agreement.
        if year is not None and candidate_year is not None:
            diff = abs(int(year) - int(candidate_year))
            if diff == 0:
                score += 20
                reasons.append('year_exact')
            elif diff == 1:
                score += 10
                reasons.append('year_close')
            elif diff == 2:
                score += 4
                reasons.append('year_near')
            else:
                score -= 15
                reasons.append('year_far')

        if not reasons:
            reasons.append('weak_signal')

        return score, ','.join(reasons)

    def _resolve_tmdb_id_with_loose_mapping(
        self,
        *,
        title: str,
        media_type: str,
        year: Optional[int],
        imdb_id: Optional[str],
        tvdb_id: Optional[str],
    ) -> Tuple[Optional[str], str]:
        """Resolve a TMDB ID via Seerr search with confidence guardrails."""
        if self.seerr is None:
            return None, 'seerr_client_missing'

        try:
            results = self.seerr.search_media(query=title, media_type=media_type, year=year)
        except Exception as e:
            logger.warning(f"Loose mapping search failed for {title}: {e}")
            return None, 'search_error'

        if not results:
            return None, 'no_candidates'

        scored: List[Tuple[int, str, Dict[str, Any], str]] = []
        for candidate in results:
            if not isinstance(candidate, dict):
                continue

            tmdb_candidate = self._extract_candidate_tmdb_id(candidate)
            if not tmdb_candidate:
                continue

            score, reason = self._score_search_candidate(
                candidate,
                title=title,
                media_type=media_type,
                year=year,
                imdb_id=imdb_id,
                tvdb_id=tvdb_id,
            )
            scored.append((score, tmdb_candidate, candidate, reason))

        if not scored:
            return None, 'no_tmdb_candidates'

        scored.sort(key=lambda row: row[0], reverse=True)
        best_score, best_tmdb, _best_candidate, best_reason = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else None

        if best_score < 65:
            return None, f'low_confidence:{best_score}'

        if second_score is not None and (best_score - second_score) < 8:
            return None, f'ambiguous:{best_score}:{second_score}'

        return best_tmdb, f'score={best_score};reason={best_reason}'
    
    def sync_seerr_request_to_jellyfin(
        self,
        seerr_user_id: str,
        media_type: str,
        tmdb_id: str,
        title: str,
        request_id: Optional[str] = None,
    ) -> bool:
        """Sync a Seerr request to Jellyfin favorite.
        
        Args:
            seerr_user_id: Seerr user ID
            media_type: 'movie' or 'tv'
            tmdb_id: TMDB ID
            title: Media title
            request_id: Optional Seerr request ID
            
        Returns:
            True if successful, False otherwise
        """
        # Get user mapping
        user_mapping = self.user_mapper.get_mapping_by_seerr_user_id(seerr_user_id)
        if not user_mapping:
            logger.warning(f"No user mapping found for Seerr user {seerr_user_id}")
            return False
        
        # Check if already synced
        existing = (
            self.db.query(SyncState)
            .filter(
                SyncState.user_mapping_id == user_mapping.id,
                SyncState.external_id == tmdb_id,
                SyncState.source == 'seerr_request',
            )
            .first()
        )
        
        if existing and existing.synced_to_jellyfin:
            logger.debug(f"Already synced to Jellyfin: {title} (TMDB: {tmdb_id})")
            return True
        
        # Search for item in Jellyfin
        jf_media_type = 'Movie' if media_type == 'movie' else 'Series'
        item = self.jellyfin.search_by_tmdb_id(tmdb_id, jf_media_type)
        
        if not item:
            # Item not in library yet, mark as pending
            if existing:
                existing.retry_count += 1
                existing.last_error = "Item not found in Jellyfin library"
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='seerr_request',
                    source_id=request_id,
                    retry_count=1,
                    last_error="Item not found in Jellyfin library",
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Item not in Jellyfin yet, marked as pending: {title}")
            return False
        
        # If already favorited, mark state as synced without calling favorite again.
        try:
            already_favorited = self.jellyfin.is_item_favorited(
                user_mapping.jellyfin_user_id,
                tmdb_id,
                jf_media_type,
            )
        except Exception as e:
            logger.warning(f"Failed favorite pre-check for {title}: {e}")
            already_favorited = False

        if already_favorited:
            if existing:
                existing.synced_to_jellyfin = True
                existing.jellyfin_item_id = item['Id']
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.last_error = None
            else:
                self.db.add(
                    SyncState(
                        user_mapping_id=user_mapping.id,
                        media_type=media_type,
                        external_id=tmdb_id,
                        title=title,
                        source='seerr_request',
                        source_id=request_id,
                        synced_to_jellyfin=True,
                        jellyfin_item_id=item['Id'],
                        last_synced_at=datetime.now(timezone.utc),
                    )
                )

            self.db.commit()
            logger.info(f"Already favorited in Jellyfin: {title}")
            return True

        # Favorite the item
        success = self.jellyfin.favorite_item(
            user_mapping.jellyfin_user_id,
            item['Id']
        )
        
        if success:
            # Update or create sync state
            if existing:
                existing.synced_to_jellyfin = True
                existing.jellyfin_item_id = item['Id']
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.last_error = None
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title,
                    source='seerr_request',
                    source_id=request_id,
                    synced_to_jellyfin=True,
                    jellyfin_item_id=item['Id'],
                    last_synced_at=datetime.now(timezone.utc),
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Favorited in Jellyfin: {title}")
            return True
        else:
            if existing:
                existing.retry_count += 1
                existing.last_error = "Failed to favorite item"
            self.db.commit()
            return False

    def _extract_seerr_request_payload(self, request: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract normalized request fields from a Seerr request payload."""
        media = request.get('media', {}) if isinstance(request, dict) else {}

        raw_media_type = str(
            media.get('mediaType')
            or request.get('mediaType')
            or request.get('type')
            or ''
        ).lower()
        media_type = 'movie' if raw_media_type == 'movie' else 'tv'

        tmdb_id = media.get('tmdbId') or request.get('mediaId')
        if tmdb_id is None:
            return None

        title = (
            media.get('title')
            or media.get('name')
            or media.get('mediaTitle')
            or request.get('subject')
            or request.get('title')
            or request.get('mediaTitle')
            or 'Unknown'
        )

        request_id = request.get('id')

        return {
            'media_type': media_type,
            'tmdb_id': str(tmdb_id),
            'title': str(title),
            'request_id': str(request_id) if request_id is not None else None,
        }

    def _build_seerr_to_jellyfin_user_map(self) -> Dict[str, str]:
        """Match Seerr users to Jellyfin users by username via ExternalUser cache.

        Returns a dict of {seerr_external_id: jellyfin_external_id} for users
        who exist in both services but have no explicit UserMapping row.
        """
        from src.database.models import ExternalUser

        seerr_users = {
            u.username.lower().strip(): u.external_id
            for u in self.db.query(ExternalUser)
            .filter(ExternalUser.service_type == "seerr")
            .all()
        }
        jellyfin_users = {
            u.username.lower().strip(): u.external_id
            for u in self.db.query(ExternalUser)
            .filter(ExternalUser.service_type == "jellyfin")
            .all()
        }
        # Intersection: username exists in both
        matched: Dict[str, str] = {}
        for name_lower, seerr_id in seerr_users.items():
            jf_id = jellyfin_users.get(name_lower)
            if jf_id:
                matched[seerr_id] = jf_id
                logger.debug(
                    "Unmapped user match: Seerr %s (%s) <-> Jellyfin %s",
                    name_lower, seerr_id, jf_id,
                )
        return matched

    def sync_seerr_completed_to_jellyfin(
        self,
        statuses: Optional[List[str]] = None,
        include_unmapped: bool = False,
    ) -> Dict[str, int]:
        """Sync Seerr completed/approved requests to Jellyfin favorites.

        This is a polling-based sync path that queries Seerr by user and status,
        then attempts to favorite matching Jellyfin items.

        When *include_unmapped* is True, Seerr users without an explicit
        UserMapping row are still synced if a matching Jellyfin user can be
        found by username (via the ExternalUser cache).
        """
        summary = {
            'users_processed': 0,
            'requests_seen': 0,
            'synced': 0,
            'pending': 0,
            'failed': 0,
            'skipped': 0,
        }

        if self.seerr is None or self.jellyfin is None:
            logger.warning("Seerr/Jellyfin client missing; skipping Seerr completed sync")
            return summary

        target_statuses = statuses or ['APPROVED', 'PROCESSING', 'AVAILABLE', 'FILLED']
        mappings = (
            self.db.query(UserMapping)
            .filter(UserMapping.is_active == True)
            .all()
        )

        seen_keys: Set[Tuple[int, str, str]] = set()

        for mapping in mappings:
            summary['users_processed'] += 1

            try:
                requests = self.seerr.get_user_requests(
                    user_id=int(mapping.seerr_user_id),
                    statuses=target_statuses,
                )
            except Exception as e:
                logger.error(f"Failed loading Seerr requests for user {mapping.seerr_user_id}: {e}")
                summary['failed'] += 1
                continue

            for request in requests:
                normalized = self._extract_seerr_request_payload(request)
                if not normalized:
                    summary['skipped'] += 1
                    continue

                key = (mapping.id, normalized['tmdb_id'], normalized['media_type'])
                if key in seen_keys:
                    summary['skipped'] += 1
                    continue
                seen_keys.add(key)

                summary['requests_seen'] += 1

                existing = (
                    self.db.query(SyncState)
                    .filter(
                        SyncState.user_mapping_id == mapping.id,
                        SyncState.external_id == normalized['tmdb_id'],
                        SyncState.source == 'seerr_request',
                    )
                    .first()
                )

                if existing and existing.synced_to_jellyfin:
                    summary['skipped'] += 1
                    continue

                success = self.sync_seerr_request_to_jellyfin(
                    seerr_user_id=str(mapping.seerr_user_id),
                    media_type=normalized['media_type'],
                    tmdb_id=normalized['tmdb_id'],
                    title=normalized['title'],
                    request_id=normalized['request_id'],
                )

                if success:
                    summary['synced'] += 1
                    continue

                refreshed = (
                    self.db.query(SyncState)
                    .filter(
                        SyncState.user_mapping_id == mapping.id,
                        SyncState.external_id == normalized['tmdb_id'],
                        SyncState.source == 'seerr_request',
                    )
                    .first()
                )

                if refreshed and (refreshed.last_error or '').startswith('Item not found in Jellyfin library'):
                    summary['pending'] += 1
                else:
                    summary['failed'] += 1

        # ── Unmapped Seerr users (username-based fallback) ──
        if include_unmapped:
            user_map = self._build_seerr_to_jellyfin_user_map()
            if user_map:
                logger.info(
                    "Unmapped-user pass: %d Seerr→Jellyfin username matches found",
                    len(user_map),
                )
            for seerr_id, jellyfin_id in user_map.items():
                summary['users_processed'] += 1
                try:
                    requests = self.seerr.get_user_requests(
                        user_id=int(seerr_id),
                        statuses=target_statuses,
                    )
                except Exception as e:
                    logger.error(
                        "Failed loading Seerr requests for unmapped user %s: %s",
                        seerr_id, e,
                    )
                    summary['failed'] += 1
                    continue

                for request in requests:
                    normalized = self._extract_seerr_request_payload(request)
                    if not normalized:
                        summary['skipped'] += 1
                        continue

                    key = (int(seerr_id), normalized['tmdb_id'], normalized['media_type'])
                    if key in seen_keys:
                        summary['skipped'] += 1
                        continue
                    seen_keys.add(key)

                    summary['requests_seen'] += 1

                    # Use the matched Jellyfin user ID directly
                    success = self._favorite_in_jellyfin_for_user(
                        jellyfin_user_id=jellyfin_id,
                        tmdb_id=normalized['tmdb_id'],
                        media_type=normalized['media_type'],
                        title=normalized['title'],
                        source='seerr_request',
                        source_id=normalized['request_id'],
                    )
                    if success:
                        summary['synced'] += 1
                    else:
                        summary['failed'] += 1

        logger.info("Seerr completed->Jellyfin sync summary: %s", summary)
        return summary

    def _favorite_in_jellyfin_for_user(
        self,
        jellyfin_user_id: str,
        tmdb_id: str,
        media_type: str,
        title: str,
        source: str = 'seerr_request',
        source_id: Optional[str] = None,
    ) -> bool:
        """Favorite a Jellyfin item for a user without requiring a UserMapping.

        Used by the unmapped-Seerr fallback path.  Persists SyncState
        records with user_mapping_id=None so the dashboard, activity
        feed, and stats reflect unmapped sync activity.
        """
        if self.jellyfin is None:
            return False

        # Use source_id (or jellyfin_user_id as fallback) to distinguish
        # unmapped records that share the same TMDB ID.
        record_source_id = source_id or jellyfin_user_id

        existing = (
            self.db.query(SyncState)
            .filter(
                SyncState.user_mapping_id == None,
                SyncState.external_id == tmdb_id,
                SyncState.source == source,
                SyncState.source_id == record_source_id,
            )
            .first()
        )

        jf_media_type = 'Movie' if media_type == 'movie' else 'Series'
        item = self.jellyfin.search_by_tmdb_id(tmdb_id, jf_media_type)
        if not item:
            if existing:
                existing.retry_count = (existing.retry_count or 0) + 1
                existing.last_error = "Item not found in Jellyfin library"
            else:
                self.db.add(SyncState(
                    user_mapping_id=None,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=title or 'Unknown',
                    source=source,
                    source_id=record_source_id,
                    retry_count=1,
                    last_error="Item not found in Jellyfin library",
                ))
            self.db.commit()
            return False

        # Use the Jellyfin item name when the Seerr title is unavailable.
        display_title = title if title and title != 'Unknown' else item.get('Name', title or 'Unknown')

        try:
            already = self.jellyfin.is_item_favorited(
                jellyfin_user_id, tmdb_id, jf_media_type,
            )
        except Exception:
            already = False

        if already:
            if existing:
                existing.synced_to_jellyfin = True
                existing.jellyfin_item_id = item['Id']
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.last_error = None
                existing.title = display_title
            else:
                self.db.add(SyncState(
                    user_mapping_id=None,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=display_title,
                    source=source,
                    source_id=record_source_id,
                    synced_to_jellyfin=True,
                    jellyfin_item_id=item['Id'],
                    last_synced_at=datetime.now(timezone.utc),
                ))
            self.db.commit()
            return True

        success = self.jellyfin.favorite_item(jellyfin_user_id, item['Id'])
        if success:
            if existing:
                existing.synced_to_jellyfin = True
                existing.jellyfin_item_id = item['Id']
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.last_error = None
                existing.title = display_title
            else:
                self.db.add(SyncState(
                    user_mapping_id=None,
                    media_type=media_type,
                    external_id=tmdb_id,
                    title=display_title,
                    source=source,
                    source_id=record_source_id,
                    synced_to_jellyfin=True,
                    jellyfin_item_id=item['Id'],
                    last_synced_at=datetime.now(timezone.utc),
                ))
            self.db.commit()
            return True
        else:
            if existing:
                existing.retry_count = (existing.retry_count or 0) + 1
                existing.last_error = "Failed to favorite item"
            self.db.commit()
            return False

    def sync_plex_watchlist_to_seerr(
        self,
        plex_username: str,
        tmdb_id: Optional[str],
        media_type: str,
        title: str,
        year: Optional[int] = None,
        imdb_id: Optional[str] = None,
        tvdb_id: Optional[str] = None,
    ) -> bool:
        """Sync Plex watchlist item to Seerr request.
        
        Args:
            plex_username: Plex username
            tmdb_id: TMDB ID (optional)
            media_type: 'movie' or 'tv'
            title: Media title
            year: Optional release year
            imdb_id: Optional IMDB ID
            tvdb_id: Optional TVDB ID
            
        Returns:
            True if successful, False otherwise
        """
        # Get user mapping
        logger.info(f"Looking up user mapping for Plex user: {plex_username}")
        user_mapping = self.user_mapper.get_mapping_by_plex_username(plex_username)
        if not user_mapping:
            logger.warning(f"No user mapping found for Plex user {plex_username}")
            # Log all available mappings for debugging
            all_mappings = self.user_mapper.get_all_mappings()
            available = [m.plex_username for m in all_mappings if m.is_active]
            logger.warning(f"Available active mappings: {available}")
            return False
        
        logger.info(f"Found user mapping: Plex={user_mapping.plex_username}, Seerr ID={user_mapping.seerr_user_id}")
        
        normalized_title = str(title or 'Unknown').strip() or 'Unknown'
        normalized_type = 'tv' if media_type == 'tv' else 'movie'
        normalized_year = self._extract_year_from_value(year)
        resolved_tmdb_id = self._normalize_tmdb_id(tmdb_id)

        unresolved_external_id = (
            f"unresolved:{normalized_type}:{self._normalize_title_for_match(normalized_title)}:"
            f"{normalized_year if normalized_year is not None else 'na'}"
        )
        lookup_external_id = resolved_tmdb_id or unresolved_external_id

        # Check if already synced
        existing = (
            self.db.query(SyncState)
            .filter(
                SyncState.user_mapping_id == user_mapping.id,
                SyncState.source == 'plex_watchlist',
                or_(
                    SyncState.external_id == lookup_external_id,
                    SyncState.external_id == unresolved_external_id,
                ),
            )
            .first()
        )

        if not resolved_tmdb_id:
            resolved_tmdb_id, resolution_reason = self._resolve_tmdb_id_with_loose_mapping(
                title=normalized_title,
                media_type=normalized_type,
                year=normalized_year,
                imdb_id=imdb_id,
                tvdb_id=tvdb_id,
            )

            if resolved_tmdb_id:
                logger.info(
                    "Loose mapping resolved TMDB ID for %s (%s): %s [%s]",
                    normalized_title,
                    normalized_type,
                    resolved_tmdb_id,
                    resolution_reason,
                )
            else:
                logger.warning(
                    "Failed to resolve TMDB ID for %s (%s). reason=%s imdb=%s tvdb=%s year=%s",
                    normalized_title,
                    normalized_type,
                    resolution_reason,
                    imdb_id,
                    tvdb_id,
                    normalized_year,
                )

                if existing:
                    existing.retry_count += 1
                    existing.last_error = f"TMDB unresolved ({resolution_reason})"
                else:
                    self.db.add(
                        SyncState(
                            user_mapping_id=user_mapping.id,
                            media_type=normalized_type,
                            external_id=unresolved_external_id,
                            title=normalized_title,
                            source='plex_watchlist',
                            retry_count=1,
                            last_error=f"TMDB unresolved ({resolution_reason})",
                        )
                    )

                self.db.commit()
                return False

        if existing and existing.external_id != resolved_tmdb_id:
            conflicting = (
                self.db.query(SyncState)
                .filter(
                    SyncState.user_mapping_id == user_mapping.id,
                    SyncState.source == 'plex_watchlist',
                    SyncState.external_id == resolved_tmdb_id,
                    SyncState.id != existing.id,
                )
                .first()
            )

            if conflicting:
                conflicting.synced_to_seerr = conflicting.synced_to_seerr or existing.synced_to_seerr
                conflicting.seerr_request_id = conflicting.seerr_request_id or existing.seerr_request_id
                conflicting.retry_count = max(conflicting.retry_count or 0, existing.retry_count or 0)
                conflicting.last_error = conflicting.last_error or existing.last_error
                conflicting.title = conflicting.title or normalized_title
                existing = conflicting
            else:
                existing.external_id = resolved_tmdb_id
                existing.media_type = normalized_type
                existing.title = normalized_title
        
        if existing and existing.synced_to_seerr:
            logger.debug(f"Already synced to Seerr: {normalized_title} (TMDB: {resolved_tmdb_id})")
            return True

        # Guard against duplicate Seerr requests: if the request already exists
        # in Seerr, mark it synced locally and skip creating a new one.
        existing_request = None
        try:
            existing_request = self.seerr.find_existing_request(
                media_type=normalized_type,
                media_id=int(resolved_tmdb_id),
                user_id=int(user_mapping.seerr_user_id),
            )
        except Exception as e:
            logger.warning(f"Failed to check existing Seerr requests for {normalized_title}: {e}")

        if existing_request:
            existing_request_id = str(existing_request.get('id')) if existing_request.get('id') is not None else None

            if existing:
                existing.synced_to_seerr = True
                existing.seerr_request_id = existing_request_id
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.last_error = None
            else:
                self.db.add(
                    SyncState(
                        user_mapping_id=user_mapping.id,
                        media_type=normalized_type,
                        external_id=resolved_tmdb_id,
                        title=normalized_title,
                        source='plex_watchlist',
                        synced_to_seerr=True,
                        seerr_request_id=existing_request_id,
                        last_synced_at=datetime.now(timezone.utc),
                    )
                )

            self.db.commit()
            logger.info(f"Seerr request already exists for {normalized_title}; marked as synced")
            return True
        
        # Create request in Seerr
        seerr_media_type = normalized_type
        logger.info(f"Creating Seerr request: {normalized_title} ({seerr_media_type}, TMDB:{resolved_tmdb_id}) for user {user_mapping.seerr_user_id}")
        
        try:
            result = self.seerr.create_request(
                media_type=seerr_media_type,
                media_id=int(resolved_tmdb_id),
                user_id=int(user_mapping.seerr_user_id),
            )
        except Exception as e:
            logger.error(f"Failed to create Seerr request: {e}", exc_info=True)
            result = None
        
        if result:
            request_id = str(result.get('id')) if result else None
            
            # Update or create sync state
            if existing:
                existing.synced_to_seerr = True
                existing.seerr_request_id = request_id
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.last_error = None
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=normalized_type,
                    external_id=resolved_tmdb_id,
                    title=normalized_title,
                    source='plex_watchlist',
                    synced_to_seerr=True,
                    seerr_request_id=request_id,
                    last_synced_at=datetime.now(timezone.utc),
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Created Seerr request: {normalized_title}")
            return True
        else:
            if existing:
                existing.retry_count += 1
                existing.last_error = "Failed to create Seerr request"
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=normalized_type,
                    external_id=resolved_tmdb_id,
                    title=normalized_title,
                    source='plex_watchlist',
                    retry_count=1,
                    last_error="Failed to create Seerr request",
                )
                self.db.add(new_state)
            
            self.db.commit()
            return False
    
    def sync_plex_watchlist_to_jellyfin(
        self,
        plex_username: str,
        tmdb_id: Optional[str],
        media_type: str,
        title: str,
        year: Optional[int] = None,
        imdb_id: Optional[str] = None,
        tvdb_id: Optional[str] = None,
    ) -> bool:
        """Sync Plex watchlist item to Jellyfin favorite.
        
        Args:
            plex_username: Plex username
            tmdb_id: TMDB ID (optional)
            media_type: 'movie' or 'tv'
            title: Media title
            year: Optional release year
            imdb_id: Optional IMDB ID
            tvdb_id: Optional TVDB ID
            
        Returns:
            True if successful, False otherwise
        """
        # Get user mapping
        user_mapping = self.user_mapper.get_mapping_by_plex_username(plex_username)
        if not user_mapping:
            logger.warning(f"No user mapping found for Plex user {plex_username}")
            return False
        
        normalized_title = str(title or 'Unknown').strip() or 'Unknown'
        normalized_type = 'tv' if media_type == 'tv' else 'movie'
        normalized_year = self._extract_year_from_value(year)
        resolved_tmdb_id = self._normalize_tmdb_id(tmdb_id)

        unresolved_external_id = (
            f"unresolved:{normalized_type}:{self._normalize_title_for_match(normalized_title)}:"
            f"{normalized_year if normalized_year is not None else 'na'}"
        )
        lookup_external_id = resolved_tmdb_id or unresolved_external_id

        # Check if already synced
        existing = (
            self.db.query(SyncState)
            .filter(
                SyncState.user_mapping_id == user_mapping.id,
                SyncState.source == 'plex_watchlist',
                or_(
                    SyncState.external_id == lookup_external_id,
                    SyncState.external_id == unresolved_external_id,
                ),
            )
            .first()
        )

        if not resolved_tmdb_id:
            resolved_tmdb_id, resolution_reason = self._resolve_tmdb_id_with_loose_mapping(
                title=normalized_title,
                media_type=normalized_type,
                year=normalized_year,
                imdb_id=imdb_id,
                tvdb_id=tvdb_id,
            )

            if not resolved_tmdb_id:
                logger.warning(
                    "Jellyfin sync skipped unresolved TMDB for %s (%s). reason=%s",
                    normalized_title,
                    normalized_type,
                    resolution_reason,
                )
                if existing:
                    existing.retry_count += 1
                    existing.last_error = f"TMDB unresolved ({resolution_reason})"
                else:
                    self.db.add(
                        SyncState(
                            user_mapping_id=user_mapping.id,
                            media_type=normalized_type,
                            external_id=unresolved_external_id,
                            title=normalized_title,
                            source='plex_watchlist',
                            retry_count=1,
                            last_error=f"TMDB unresolved ({resolution_reason})",
                        )
                    )
                self.db.commit()
                return False

        if existing and existing.external_id != resolved_tmdb_id:
            conflicting = (
                self.db.query(SyncState)
                .filter(
                    SyncState.user_mapping_id == user_mapping.id,
                    SyncState.source == 'plex_watchlist',
                    SyncState.external_id == resolved_tmdb_id,
                    SyncState.id != existing.id,
                )
                .first()
            )

            if conflicting:
                conflicting.synced_to_jellyfin = conflicting.synced_to_jellyfin or existing.synced_to_jellyfin
                conflicting.jellyfin_item_id = conflicting.jellyfin_item_id or existing.jellyfin_item_id
                conflicting.synced_to_seerr = conflicting.synced_to_seerr or existing.synced_to_seerr
                conflicting.seerr_request_id = conflicting.seerr_request_id or existing.seerr_request_id
                conflicting.retry_count = max(conflicting.retry_count or 0, existing.retry_count or 0)
                conflicting.last_error = conflicting.last_error or existing.last_error
                conflicting.title = conflicting.title or normalized_title
                self.db.delete(existing)
                existing = conflicting
            else:
                existing.external_id = resolved_tmdb_id
                existing.media_type = normalized_type
                existing.title = normalized_title
        
        if existing and existing.synced_to_jellyfin:
            logger.debug(f"Already favorited in Jellyfin: {normalized_title} (TMDB: {resolved_tmdb_id})")
            return True
        
        # Search for item in Jellyfin
        jf_media_type = 'Movie' if normalized_type == 'movie' else 'Series'
        item = self.jellyfin.search_by_tmdb_id(resolved_tmdb_id, jf_media_type)
        
        if not item:
            # Item not in library yet
            if existing:
                existing.retry_count += 1
                existing.last_error = "Item not found in Jellyfin library"
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=normalized_type,
                    external_id=resolved_tmdb_id,
                    title=normalized_title,
                    source='plex_watchlist',
                    retry_count=1,
                    last_error="Item not found in Jellyfin library",
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Item not in Jellyfin yet, marked as pending: {normalized_title}")
            return False
        
        # Favorite the item
        success = self.jellyfin.favorite_item(
            user_mapping.jellyfin_user_id,
            item['Id']
        )
        
        if success:
            # Update or create sync state
            if existing:
                existing.synced_to_jellyfin = True
                existing.jellyfin_item_id = item['Id']
                existing.last_synced_at = datetime.now(timezone.utc)
                existing.last_error = None
            else:
                new_state = SyncState(
                    user_mapping_id=user_mapping.id,
                    media_type=normalized_type,
                    external_id=resolved_tmdb_id,
                    title=normalized_title,
                    source='plex_watchlist',
                    synced_to_jellyfin=True,
                    jellyfin_item_id=item['Id'],
                    last_synced_at=datetime.now(timezone.utc),
                )
                self.db.add(new_state)
            
            self.db.commit()
            logger.info(f"Favorited in Jellyfin: {normalized_title}")
            return True
        else:
            if existing:
                existing.retry_count += 1
                existing.last_error = "Failed to favorite item"
            self.db.commit()
            return False
    
    def retry_pending_items(self, max_age_days: int = 7) -> int:
        """Retry syncing pending items.
        
        Args:
            max_age_days: Maximum age of items to retry
            
        Returns:
            Number of items successfully synced
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        
        pending = (
            self.db.query(SyncState)
            .filter(
                SyncState.synced_to_jellyfin == False,
                SyncState.first_seen_at > cutoff_date,
                SyncState.retry_count < 10,
            )
            .all()
        )
        
        success_count = 0
        
        for item in pending:
            user_mapping = (
                self.db.query(UserMapping)
                .filter(UserMapping.id == item.user_mapping_id)
                .first()
            )
            
            if not user_mapping:
                continue
            
            # Try to sync based on source
            if item.source == 'seerr_request':
                success = self.sync_seerr_request_to_jellyfin(
                    user_mapping.seerr_user_id,
                    item.media_type,
                    item.external_id,
                    item.title or "Unknown",
                    item.source_id,
                )
            elif item.source == 'plex_watchlist':
                success = self.sync_plex_watchlist_to_jellyfin(
                    user_mapping.plex_username,
                    item.external_id,
                    item.media_type,
                    item.title or "Unknown",
                )
            else:
                continue
            
            if success:
                success_count += 1
        
        return success_count
    
    def get_stats(self) -> dict:
        """Get sync statistics.
        
        Returns:
            Dictionary with sync statistics
        """
        total = self.db.query(SyncState).count()
        synced_jf = self.db.query(SyncState).filter(SyncState.synced_to_jellyfin == True).count()
        synced_seerr = self.db.query(SyncState).filter(SyncState.synced_to_seerr == True).count()
        pending = self.db.query(SyncState).filter(SyncState.synced_to_jellyfin == False).count()

        seerr_query = self.db.query(SyncState).filter(SyncState.source == 'seerr_request')
        seerr_total = seerr_query.count()
        seerr_synced = seerr_query.filter(SyncState.synced_to_jellyfin == True).count()
        seerr_pending = seerr_query.filter(
            SyncState.synced_to_jellyfin == False,
            SyncState.retry_count < 3,
        ).count()
        seerr_failed = seerr_query.filter(
            SyncState.synced_to_jellyfin == False,
            SyncState.retry_count >= 3,
        ).count()

        return {
            'total_items': total,
            'synced_to_jellyfin': synced_jf,
            'synced_to_seerr': synced_seerr,
            'pending': pending,
            'seerr_request': {
                'total': seerr_total,
                'synced_to_jellyfin': seerr_synced,
                'pending': seerr_pending,
                'failed': seerr_failed,
            },
        }
