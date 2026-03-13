# Issues and Feature Requests

## Status Snapshot

Updated after latest sync debugging and retest cycle.

## Bugs

### Issue 1: User Mapping UI Shows Incorrect Count
- **Status**: ✅ Completed
- **Resolution**: User counting logic and UI messaging were aligned so counts are no longer contradictory.

### Issue 2: Servers UI Formatting
- **Status**: ⏳ Open
- **Notes**: Cosmetic spacing improvement still optional.

### Issue 3: Add Server Form Asks for Unnecessary Name
- **Status**: ⏳ Open / Backlog
- **Notes**: Still a product/UI design enhancement rather than a blocking sync bug.

### Issue 4: Server Save Shows Error Despite Success
- **Status**: ✅ Completed
- **Resolution**: API/UI error handling updated so successful saves no longer surface as failures.

### Issue 5: Service Type Defaults are Wrong
- **Status**: ✅ Completed
- **Resolution**: Service-specific defaults now populate correctly for Plex/Jellyfin/Seerr.

## Active Development Issues (Sync Pipeline)

### Issue 6: Plex Friend Watchlist Sync - Only Fetching 2 of 3 Mapped Users
- **Status**: ✅ Completed
- **Root Cause**: Username normalization mismatch (case/spacing).
- **Resolution**: Normalized friend/mapping comparison.

### Issue 7: Watchlist Items Not Syncing to Seerr
- **Status**: ✅ Completed
- **Root Cause(s) Resolved**:
  1. Runtime sync-engine entrypoints were not consistently receiving loaded config/feature flags.
  2. Plex GraphQL media type normalization incorrectly mapped uppercase GraphQL types.
  3. TV requests to Seerr were missing season selection in payload in this deployment.
- **Resolution**:
  - Passed config into sync engine construction across runtime paths.
  - Fixed GraphQL media-type normalization for `MOVIE/SHOW` handling.
  - Added `seasons: 'all'` for TV requests in Seerr request payload.
- **Verification**: Latest rebuild + manual sync run completed with successful Seerr request creation and no Seerr API 500s in the validation window.

### Issue 8: Missing Debug Visibility
- **Status**: ✅ Completed
- **Resolution**: Critical pipeline logging promoted to INFO for runtime traceability.

### Issue 9: Seerr User Pagination
- **Status**: ✅ Completed
- **Resolution**: Pagination loop added to fetch all Seerr users.

### Issue 10: Plex GraphQL UUID vs Numeric ID
- **Status**: ✅ Completed
- **Resolution**: UUID lookup path added for GraphQL user access.

### Issue 11: Not Syncing some mapped users
- **Status**: ⏳ Partially Fixed / Open
- **Resolved**:
  - Mapped-user candidate discovery now includes account owner + friends + managed users.
  - Username matching is normalized (case/space-insensitive) when resolving mapped users.
  - GraphQL watchlist fetch now supports multiple ID candidates per user and retries on `User not found` for candidate fallback.
  - Verified working for newly mapped users (for example `OliviaRomkes`).
- **Still Open**:
  - One mapped user (`Tory Malpass` / Victoria mapping) still fails in Plex GraphQL with:
    - `User not found: Data loader item not found: users uuid=198975710`
  - This user remains fetchable in mapping selection but returns `0` watchlist items due to GraphQL user-resolution failure.
- **Notes**:
  - `carolyn16` now resolves and fetches correctly, but currently has `0` watchlist items.
  - Keep this issue open pending a robust workaround for that specific Plex account edge case.

### clear out references to jane and john plex that is autocreated in mappings every rebuild / restart

## Feature Requests

## Suggestion: Loose content mapping
- it seems not all imdb media is being found or being matched in seerr from plex watchlist. build a smart loose mapping functionality to improve the chance of a "hit" 
- this may require an additional api enpoint from the plex watchlist functionality, research may be required

## Suggestion: Ensure Only new items sync from watchlist and are requested in seerr
- **Status**: ✅ Completed
- **Priority**: High
- **Resolution**:
  - Added Seerr request pagination + lookup helpers to detect existing requests.
  - Sync path now marks items as synced when a matching remote request already exists, instead of creating duplicates.
  - New requests are only created when no existing request is found for `(media_type, media_id, user_id)`.

### Suggestion: Add Test Connection Button
- **Status**: 💡 Backlog

### Suggestion: Unified Service Configuration Page
- **Status**: 💡 Backlog

### Feature Request: Export/Import Configuration
- **Status**: 💡 Backlog
- **Priority**: Medium

### Feature Request: Per mapping user sync
- ** Status** backlog
- **Priority**: Low

### Feature request: Dashboard Sync Stats
Add UI Element that shows failed synced items and successful. Right now UI shows 
Servers Connected - Users Mapped - Items Synced - Pending Items
Perhaps Change it to
Servers Connected - Users Mapped - Items Synced - Failed Items
Or a breakdown watchlist syncing and favourites syncing?
watchlist vs items synced vs items failed
and then favourites from seerr and favourites synced to jellyfin
-- **Status** backlog
- *Priority**:medium

## Technical Debt / Follow-up

- Optional cleanup: downgrade temporary high-volume diagnostics once stable behavior is confirmed in longer running production use.
