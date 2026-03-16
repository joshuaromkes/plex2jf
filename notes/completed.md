# Completed Issues and Tasks

## Features & Improvements

### Loose Content Mapping (Improved Match Hit Rate)
**Date Completed**: 2026-03-16
**Description**: Implemented strict-ID-first matching with title/year/type fallback and confidence guardrails to improve request hit rates when strict IDs fail.
**Outcome Details**:
1.  Kept strict ID-first flow (`tmdb`, `imdb`, `tvdb`) as primary path.
2.  Added fallback title/year/type search with confidence scoring and ambiguity guardrails.
3.  Added unresolved-item persistence with synthetic IDs to avoid null `external_id` writes and preserve retries.
4.  Added Seerr `/search` retry behavior (query-only) when optional filters are rejected.
5.  Added regression tests for fallback resolution and unresolved-item handling.
6.  Rebuild verification logged successful completion: `Plex watchlist poll complete. Synced 1100 items.`

### Frontend UI Improvements
**Description**: Redesigned User Mapping page and improved server management UI.
**Outcome Details**:
-   User Mapping page redesigned as a table with inline editing and searchable dropdowns.
-   Added per-mapping statistics (watchlist and Seerr request counts) via new `/api/users/mappings/stats` endpoint.
-   "Add Mapping" now inserts a new row directly into the table (no separate modal).
-   Servers page spacing improved (`space-y-6`, larger gaps, better modal padding).
-   Server form name field made optional with clear hint text and auto-generated placeholder.
-   Updated frontend types (`UserMappingStats`) and API service to support new stats.
-   Created [`notes/ui-improvements-plan.md`](notes/ui-improvements-plan.md) documenting the changes.

## Bug Fixes & Refactorings

### User Mapping UI Shows Incorrect Count
**Description**: Resolved an issue where the User Mapping UI displayed incorrect counts.

### Server Save Shows Error Despite Success
**Description**: Fixed an issue where saving server configurations incorrectly displayed an error message even when the operation was successful.

### Service Type Defaults are Wrong
**Description**: Corrected incorrect default values for service types.

### Servers UI Formatting
**Description**: Enhanced server UI formatting for improved user experience.
**Outcome Details**:
-   Increased vertical spacing (`space-y-6`).
-   Improved modal padding.

### Add Server Form Asks for Unnecessary Name
**Description**: Modified the "Add Server" form to make the name field optional.
**Outcome Details**:
-   Name field now optional with clear hint text.
-   Auto-generated name shown in placeholder.

### Auto-Created `john_plex` / `jane_plex` Mapping Noise on Restart
**Description**: Mitigated the issue of noisy auto-created example mappings on restart.
**Outcome Details**:
-   Added detection and skipping of example/placeholder mappings in `UserMapper.sync_user_mappings()`.
-   Example usernames (`john_plex`, `jane_plex`) and placeholder IDs (`abc123`, `def456`, etc.) are now ignored during config sync.
-   Existing placeholder mappings can be manually deleted; they will not be recreated on restart.

### Plex Friend Watchlist Sync - Only Fetching 2 of 3 Mapped Users
**Description**: Fixed an issue where Plex friend watchlist sync was only fetching a partial set of mapped users.
**Outcome Details**: Plex friend username normalization mismatch resolved; all 3 mapped users now included.

### Watchlist Items Not Syncing to Seerr
**Description**: Resolved an issue preventing watchlist items from syncing to Seerr.

### Missing Debug Visibility
**Description**: Improved debug visibility for relevant processes.

### Seerr User Pagination
**Description**: Implemented or fixed pagination for Seerr user lists.

### Plex GraphQL UUID vs Numeric ID
**Description**: Addressed discrepancies related to Plex GraphQL UUIDs versus Numeric IDs.

### Not Syncing Some Mapped Users (Tory)
**Description**: Fixed an issue where specific mapped users (e.g., "Tory") were not syncing.

### Sync Count vs Request Success Mismatch (Loose Outcome Accounting)
**Description**: Resolved discrepancies between sync counts and actual request success due to loose outcome accounting.

## Sync Pipeline Work

### Seerr Sync Flag/Runtime Config Wiring
**Description**: Fixed wiring for Seerr sync flags and runtime configuration across manual, scheduler, and webhook paths.

### GraphQL Media-Type Normalization
**Description**: Corrected GraphQL media-type normalization (handling MOVIE/SHOW).

### TV Request Payload Shape for Seerr
**Description**: Fixed the TV request payload shape for Seerr (`seasons: 'all'`).

### Rebuild + Verify Manual Sync End-to-End
**Description**: Performed and verified end-to-end manual sync rebuild.

### Expand Mapped-User Discovery
**Description**: Expanded mapped-user discovery to include account owner, friends, and managed users.

### Add Seerr Existing-Request Lookup
**Description**: Added Seerr existing-request lookup to prevent duplicate watchlist requests.

### Add GraphQL User-ID Candidate Fallback
**Description**: Implemented GraphQL user-ID candidate fallback for [`src/services/user_mapper.py`](src/services/user_mapper.py).

## Seerr→Jellyfin Sync Implementation
**Description**: Developed and integrated Seerr to Jellyfin sync functionality.
**Outcome Details**:
-   Researched Seerr API for fetching completed/approved/available requests per user (statuses: APPROVED, PROCESSING, AVAILABLE, FILLED).
-   Enhanced [`src/api/seerr.py`](src/api/seerr.py) to add `get_user_requests()` to filter by user and status.
-   Updated [`src/services/sync_engine.py`](src/services/sync_engine.py) to add `sync_seerr_completed_to_jellyfin()` with Jellyfin search and favorite logic.
-   Enhanced `SyncEngine.get_stats()` to add counters for `source='seerr_request'` (total/synced/pending/failed).
-   Integrated poller: added `poll_seerr_requests_to_jellyfin()` called by scheduler every 30 minutes.
-   Optional: Verified [`src/api/jellyfin.py`](src/api/jellyfin.py) `is_item_favorited()` for verification.
-   Updated Dashboard UI and API to display Seerr-to-Jellyfin sync statistics.
-   Added unit tests for new Seerr and sync engine functionality.
-   Updated [`plans/seerr-to-jellyfin-sync.md`](plans/seerr-to-jellyfin-sync.md) with polling-based architecture diagram.
-   Kept/enhanced webhook handler for real-time sync of single requests.
-   Updated [`notes/issues.md`](notes/issues.md) Issue 12 with resolution details.
-   Verified Seerr-to-Jellyfin sync is working (logs show successful favorites).
-   Removed `watchlistarr` directory after finding relevant info; dependencies were re-implemented to remove the directory.

## Miscellaneous
-   Configured auto-creation for config file when missing.
-   Validated Docker volume mapping for config/data persistence.
-   Added root API endpoint at [`localhost:8000`](localhost:8000).
