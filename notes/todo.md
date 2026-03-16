# To-Do List

## Current Sprint / High Priority
- [ ] Frontend authentication: Implement authentication following best practices (web auth and/or HTTP auth) and allow admin control in settings.
- [ ] In user mapping dropdowns, hide users already mapped to avoid duplicate mappings.
- [ ] Simplify User Mapping UI stats for Plex Watchlist and Seerr Requests to show Total and Failed only.
  - Clarify wording for "Seerr Stats" to reduce ambiguity.
- [ ] Fix Frontend Seerr Request Sync stats not working.
- [ ] Fix Dashboard Pending Items / Seerr counters showing 0 despite sync activity.

## Backlog / Future Improvements
- [ ] Add explicit Test Connection UX in the add-server flow.
- [ ] Add export/import functionality for servers, mappings, and application settings.
- [ ] Optional: Reduce temporary high-volume diagnostic logging after a stability window.
- [ ] Optional: Monitor loose-match precision/recall and tune scoring thresholds if false positives appear.
- [ ] Implement a table-type form with dropdowns for user mapping, replacing separate forms/buttons.
  - Include integrated button to trigger watchlist sync.
  - Display watchlist item count, request count, and manual sync options for watchlist & favorites.
- [ ] Fully build out logging levels and implement a live log viewer within the web frontend.
- [ ] Address the issue where logging settings currently do not affect [`plex2jf.log`](plex2jf.log) or web UI output.
