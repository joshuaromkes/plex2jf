# Issues and Feature Requests

## Status Snapshot

Updated after the latest Plex GraphQL/Tory retest cycle.

### Current Priority
1. Improve request outcome visibility (high sync count vs true successful requests).
2. Add loose content mapping to improve hit rate for unmatched Plex items.

---

## Bugs


## Feature Requests

### Feature: Loose Content Mapping (Improved Match Hit Rate)
- **Status**: ⏳ Open
- **Priority**: High
- **Problem**:
  - Not all Plex watchlist items map cleanly to Seerr requests via current ID path.
  - See logs in plex2jf.log referencing no TMDBID
- **Goal**:
  - Add a smart loose-matching fallback to improve request hit rate when strict IDs fail.
- **Candidate Approach**:
  1. Keep strict ID-first flow (`tmdb`, `imdb`, `tvdb`) as primary.
  2. If strict lookup fails, fallback to title/year/type search with confidence scoring.
  3. Record why fallback matched (or failed) in logs for auditability.
  4. Add guardrails to prevent false-positive requests.
- **Research Note**:
  - May require additional Plex metadata/query coverage for better disambiguation.

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
