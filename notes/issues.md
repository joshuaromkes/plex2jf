# Issues and Feature Requests

### Current Priority
1. Fix frontend Seerr Request Sync stats showing `0` despite active sync history.
2. Validate dashboard pending/request counters against database-backed sync state.
3. Reduce temporary high-volume diagnostics after a stability window.

---

## Bugs

### UI Freezes During Sync
- **Description**: The UI freezes until the sync process is complete.

### UI Display Issues & Bugfix/Feature Request Combo
1.  **Request Outcome Visibility**: Improve clarity on request outcomes (distinguish high sync count from truly successful requests).
    -   See [`todo.md`](notes/todo.md) for inquiries regarding improved User Mapping UI as both a bugfix and a feature request.
    -   **Current State**: Seerr Stats column currently shows '0' for all stats: "45 total /45 synced /0 pending /0 failed" | "0 total /0 synced /0 pending /0 failed".
2.  **Dashboard Pending Items**: Dashboard displays "Pending Items 0" despite pending items existing.
3.  **Dashboard Seerr Request Sync**: All UI elements for Seerr Request Sync show '0' items.
    -   Total Requests: 0 Seerr requests tracked
    -   Synced to Jellyfin: 0 Favorited in Jellyfin
    -   Pending: 0 Waiting for library item
    -   Failed: 0 Exceeded retry limit

## Feature Requests

### Suggestion: Add Test Connection Button
-   **Status**: 💡 Backlog

### Suggestion: Unified Service Configuration Page
-   **Status**: 💡 Backlog

### Feature Request: Export/Import Configuration
-   **Status**: 💡 Backlog
-   **Priority**: Medium

### Feature Request: Per-Mapping User Sync
-   **Status**: 💡 Backlog
-   **Priority**: Low

### Feature Request: Separate Sync Buttons
-   Separate buttons for favorites sync, watchlist sync, and user sync from the dashboard.

### Feature Request: Enhanced User Mapping UI
-   Create a table-type form with dropdowns for each user instead of separate forms/buttons for each.
-   Include Excel-style table with integrated button to trigger watchlist sync, stats on watchlist item count, request count, and manual sync for watchlist & favorites.

### Feature Request: Comprehensive Logging & Live Viewer
-   Fully build out logging levels and integrate a live log viewer within the web frontend.
-   **Issue**: Currently, logging settings do not affect [`plex2jf.log`](plex2jf.log) or web UI output.

### Bug: Frontend Seerr Request Sync Stats Not Working
-   **Description**: The frontend display for Seerr Request Sync statistics is non-functional.

## Technical Debt / Follow-up

-   **Logging Cleanup**: Optional cleanup to downgrade temporary high-volume diagnostics once stable behavior is confirmed in longer-running production use.
-   **Loose Match Monitoring**: Optional follow-up to continue monitoring loose-match precision/recall and tune scoring thresholds if false positives appear.
