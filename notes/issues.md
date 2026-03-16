# Issues and Feature Requests


### Current Priority
1. Fix frontend Seerr Request Sync stats showing `0` despite active sync history.
2. Validate dashboard pending/request counters against database-backed sync state.
3. Reduce temporary high-volume diagnostics after a stability window.

---

## Bugs

## When syncing, UI freezes until sync is complete

## UI Issues, Bugfix & Feature Request Combo
1. Improve request outcome visibility (high sync count vs true successful requests).
  A. See todo.md for improved User Mapping UI inquiries as both a bugfix AND a FR
  B. Seerr Stats column currently shows 0 for all stats: 45 total /45 synced /0 pending /0 failed|0 total /0 synced /0 pending /0 failed
2. Dashboard: Pending Items returns 0 items: Pending Items 0
3. Dashboard: Seerr Request Sync returns 0 items for all UI elements: 
    Total Requests 0 Seerr requests tracked
    Synced to Jellyfin 0 Favorited in Jellyfin
    Pending 0 Waiting for library item
    Failed 0 Exceeded retry limit




### Feature: Loose Content Mapping (Improved Match Hit Rate)
- **Status**: ✅ Completed (2026-03-16)
- **Priority**: High
- **Problem**:
  - Not all Plex watchlist items map cleanly to Seerr requests via current ID path.
  - See logs in plex2jf.log referencing no TMDBID
- **Goal**:
  - Add a smart loose-matching fallback to improve request hit rate when strict IDs fail.
- **Implemented Outcome**:
  1. Kept strict ID-first flow (`tmdb`, `imdb`, `tvdb`) as primary path.
  2. Added fallback title/year/type search with confidence scoring and ambiguity guardrails.
  3. Added unresolved-item persistence with synthetic IDs to avoid null `external_id` writes and preserve retries.
  4. Added Seerr `/search` retry behavior (query-only) when optional filters are rejected.
  5. Added regression tests for fallback resolution and unresolved-item handling.
  6. Rebuild verification logged successful completion: `Plex watchlist poll complete. Synced 1100 items.`

### Suggestion: Add Test Connection Button
- **Status**: 💡 Backlog

### Suggestion: Unified Service Configuration Page
- **Status**: 💡 Backlog

### Feature Request: Export/Import Configuration
- **Status**: 💡 Backlog
- **Priority**: Medium

### Feature Request: Per-Mapping User Sync
- **Status**: 💡 Backlog
- **Priority**: Low

- ### Feature Request: Separate buttons for favourites sync, and watchlist sync and user sync from dashboard
- ### Feature Request: Under user mapping. create a table type form with dropdowns for each user instead of a separate form / button for each. See excel style tabling with integrated button to trigger a watchlist sync, stat on watchlist item count, request count and manual sync for watchlist & faves.
### Feature Request: Fully build out logging levels, and a live log viewer within web frontend.
- Issue: right now logging under settings does nothing in terms of log output to plex2jf.log or webui output. 

- ### Issue: Frontend Seer Request Sync stats not working
## Technical Debt / Follow-up

- Optional cleanup: downgrade temporary high-volume diagnostics once stable behavior is confirmed in longer-running production use.
- Optional follow-up: continue monitoring loose-match precision/recall and tune scoring thresholds if false positives appear.
