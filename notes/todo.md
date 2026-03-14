**Backlog / Next Improvements**
- [ ] Add explicit Test Connection UX in add-server flow
- [ ] Add export/import for servers, mappings, and app settings
- [ ] Optional: reduce temporary high-volume diagnostic logging after stability window


# Current To-Do List

- Frontend Authentication, implement authentication following best practices. allow web page auth or http auth. allow admin to change in settings.
- In the user mapping dropdowns when mapping new users, hide users already mapped to not map them twice

## High-Priority Issues
- Feature: Loose Content Mapping (Improved Match Hit Rate)

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