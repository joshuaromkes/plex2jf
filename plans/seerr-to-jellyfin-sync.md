# Seerr Completed Requests → Jellyfin Favorites Sync (Polling)

**Status: Implemented (See notes/completed.md for details)**

## Simple Explanation
Instead of waiting for Seerr webhooks (which your version lacks for 'fulfilled'), the app will **automatically check Seerr every 15 minutes** for all approved/available requests from mapped users.

For each such request:
1. See if we've already favorited it in Jellyfin (via database check)
2. If not, search Jellyfin library for the movie/TV show using TMDB ID
3. If found in library → add to user's favorites
4. If not found → wait for next poll (when *Arr downloads & scans it)
5. Track everything in database for stats & retries

**Benefits:**
- Works with **historical requests** (past approvals)
- No Seerr config changes needed
- Handles delays (approval → download → scan)
- Accurate stats (synced vs pending vs failed)

## Seerr Request Statuses
From API: `request.status` values like:
- `PENDING` / `SEARCHING`
- `APPROVED`
- `PROCESSING`
- `AVAILABLE` / `FILLED`

We'll sync on `APPROVED`, `PROCESSING`, `AVAILABLE` (safe to favorite early, JF search confirms availability).

## Detailed Flow (runs every 15min)
```
1. Get all active UserMappings (Plex/Seerr/JF users linked)
2. For each mapping:
   - Fetch user's requests from Seerr API (filter APPROVED+)
   - For each request:
     - Extract TMDB ID, type (movie/tv), title
     - Check local SyncState DB (already handled?)
     - Search Jellyfin: /Items?AnyProviderIdEquals=tmdb.123456 (recursive)
     - If item found & not favorite → POST favorite
     - Update DB: synced=True or pending/error
```

Mermaid diagram:
```mermaid
graph LR
  A[Every 15min Poller] --> B{Active Mappings?}
  B -->|Yes| C[Get Seerr User Requests<br/>(APPROVED/AVAILABLE)]
  C --> D{New/Unsynced?}
  D -->|Yes| E[Search JF by TMDB ID]
  E --> F{Item in Library?}
  F -->|Yes| G[Favorite Item] --> H[DB: Synced ✓]
  F -->|No| I[DB: Pending ⏳<br/>Retry Next Poll]
  D -->|No| J[Skip]
  B -->|No| K[No Mappings]
```

## Where Code Changes
- SeerrClient: `get_user_requests(user_id, min_status='APPROVED')`
- SyncEngine: `sync_seerr_requests_to_jellyfin()`
- PollerService: call new sync in poll loop
- Scheduler: already polls every X sec (config.sync.polling_interval)
- Dashboard: show stats from SyncEngine.get_stats()

## Next: Code Implementation
Once approved, switch to 💻 Code mode.

## Manual Test
Add endpoint /debug/sync-seerr-to-jf to trigger once.
