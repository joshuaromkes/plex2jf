# Completed Issues and Tasks

## From notes/issues.md

### Bugs
- Issue 1: User Mapping UI Shows Incorrect Count
- Issue 4: Server Save Shows Error Despite Success
- Issue 5: Service Type Defaults are Wrong

### Active Development Issues (Sync Pipeline)
- Issue 6: Plex Friend Watchlist Sync - Only Fetching 2 of 3 Mapped Users
- Issue 7: Watchlist Items Not Syncing to Seerr
- Issue 8: Missing Debug Visibility
- Issue 9: Seerr User Pagination
- Issue 10: Plex GraphQL UUID vs Numeric ID
- Issue 11: Not Syncing Some Mapped Users (Tory)
- Issue 12: Sync Count vs Request Success Mismatch (Loose Outcome Accounting)

### Feature Requests
- Suggestion: Ensure Only New Items Sync from Watchlist and Are Requested in Seerr
- Feature Request: Dashboard Sync Stats Breakdown

## From notes/todo.md

- Configure auto-create for config file when missing
- Validate Docker volume mapping for config/data persistence
- Add root API endpoint at localhost:8000

**Primary Goal (UI-first operation instead of config-first)**
- Build user-friendly frontend for server setup (Plex/Jellyfin/Seerr)
- Build UI for user mapping management
- Build UI proof of concept following Arr-style direction from ./notes/arrdesign.md
- Implement server management UI workflows (create/edit/delete/test)
- Implement user refresh in UI (pull users from Plex/Jellyfin/Seerr)
- Implement mapping workflow in UI (Plex user to Jellyfin/Seerr identities)

**Recent Sync Pipeline Work (Completed)**
- Fix Plex friend username normalization mismatch (3 mapped users now included)
- Fix Seerr sync flag/runtime config wiring across manual/scheduler/webhook paths
- Fix GraphQL media-type normalization (MOVIE/SHOW handling)
- Fix TV request payload shape for Seerr (`seasons: 'all'`)
- Rebuild + verify manual sync end-to-end
- Expand mapped-user discovery to include account owner + friends + managed users
- Add Seerr existing-request lookup to avoid duplicate watchlist requests
- Add GraphQL user-id candidate fallback for user_mapping.py

**Seerr→Jellyfin Sync Implementation (Completed)**
- Research Seerr API for fetching completed/approved/available requests per user (statuses: APPROVED, PROCESSING, AVAILABLE, FILLED)
- Enhance src/api/seerr.py: add get_user_requests() to filter by user and status
- Update src/services/sync_engine.py: add sync_seerr_completed_to_jellyfin() with Jellyfin search and favorite logic
- Enhance SyncEngine.get_stats(): add counters for source='seerr_request' (total/synced/pending/failed)
- Integrate poller: add poll_seerr_requests_to_jellyfin() called by scheduler every 30 minutes
- Optional: src/api/jellyfin.py is_item_favorited() for verification
- Update Dashboard UI and API to display Seerr→Jellyfin sync statistics
- Add unit tests for new Seerr and sync engine functionality
- Update plans/seerr-to-jellyfin-sync.md with polling‑based architecture diagram
- Keep/enhance webhook handler for real‑time sync of single requests
- Update notes/issues.md Issue 12 with resolution details
- Verify Seerr→Jellyfin sync is working (logs show successful favorites)
- Need to remove watchlistarr directory from project, it was a repo used to find info on plex watchlist pulling, Need to find deps and remove / reimplement to remove dir

**Frontend UI Improvements (Completed)**
- User Mapping page redesigned as a table with inline editing and searchable dropdowns
- Added per‑mapping statistics (watchlist and Seerr request counts) via new `/api/users/mappings/stats` endpoint
- “Add Mapping” now inserts a new row directly into the table (no separate modal)
- Servers page spacing improved (`space-y-6`, larger gaps, better modal padding)
- Server form name field made optional with clear hint text and auto‑generated placeholder
- Updated frontend types (`UserMappingStats`) and API service to support new stats
- Created `notes/ui-improvements-plan.md` documenting the changes
