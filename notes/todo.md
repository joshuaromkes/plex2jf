**Backlog / Next Improvements**
- [ ] Add explicit Test Connection UX in add-server flow
- [ ] Add export/import for servers, mappings, and app settings
- [ ] Optional: reduce temporary high-volume diagnostic logging after stability window
- [ ] Optional: monitor loose-match precision/recall and tune scoring thresholds if false positives appear


# Current To-Do List

- Frontend authentication: implement auth following best practices (web auth and/or HTTP auth) and allow admin control in settings.
- In user mapping dropdowns, hide users already mapped to avoid duplicate mappings.
- Simplify User Mapping UI stats for Plex Watchlist and Seerr Requests to show Total and Failed only.
    - Clarify wording for "Seerr Stats" to reduce ambiguity.

## High-Priority Issues
- Issue: Frontend Seerr Request Sync stats not working
- Issue: Dashboard Pending Items / Seerr counters showing 0 despite sync activity

## Bugs
- Issue: Frontend Seer Request Sync stats not working

## Feature Requests
- Suggestion: Add Test Connection Button
- Suggestion: Unified Service Configuration Page
- Feature Request: Export/Import Configuration
- Feature Request: Per-Mapping User Sync
- Feature Request: Separate buttons for favourites sync, and watchlist sync and user sync from dashboard
- Feature Request: Under user mapping. create a table type form with dropdowns for each user instead of a separate form / button for each. See excel style tabling with integrated button to trigger a watchlist sync, stat on watchlist item count, request count and manual sync for watchlist & faves.
- Feature Request: Fully build out logging levels, and a live log viewer within web frontend.

## Technical Debt / Follow-up
- Optional cleanup: downgrade temporary high-volume diagnostic logging once stable behavior is confirmed in longer-running production use.
- Optional follow-up: continue monitoring loose content mapping match quality in production.
