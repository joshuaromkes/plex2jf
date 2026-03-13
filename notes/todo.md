- [x] Configure auto-create for config file when missing
- [x] Validate Docker volume mapping for config/data persistence
      volumes:
      - ./config:/app/config/
      - ./data:/data
- [x] Add root API endpoint at localhost:8000

**Primary Goal (UI-first operation instead of config-first)**
- [x] Build user-friendly frontend for server setup (Plex/Jellyfin/Seerr)
- [x] Build UI for user mapping management
- [x] Build UI proof of concept following Arr-style direction from ./notes/arrdesign.md
- [x] Implement server management UI workflows (create/edit/delete/test)
- [x] Implement user refresh in UI (pull users from Plex/Jellyfin/Seerr)
- [x] Implement mapping workflow in UI (Plex user to Jellyfin/Seerr identities)

**Recent Sync Pipeline Work (Completed)**
- [x] Fix Plex friend username normalization mismatch (3 mapped users now included)
- [x] Fix Seerr sync flag/runtime config wiring across manual/scheduler/webhook paths
- [x] Fix GraphQL media-type normalization (MOVIE/SHOW handling)
- [x] Fix TV request payload shape for Seerr (`seasons: 'all'`)
- [x] Rebuild + verify manual sync end-to-end
- [x] Expand mapped-user discovery to include account owner + friends + managed users
- [x] Add Seerr existing-request lookup to avoid duplicate watchlist requests
- [x] Add GraphQL user-id candidate fallback for managed users

**Backlog / Next Improvements**
- [ ] Investigate Plex GraphQL user-resolution edge case for `Tory Malpass` / Victoria mapping (`User not found ... users uuid=198975710`)
- [ ] Issue 2: Servers page spacing polish
- [ ] Issue 3: Rework add-server form (auto-name + IP/Port UX)
- [ ] Add explicit Test Connection UX in add-server flow
- [ ] Add export/import for servers, mappings, and app settings
- [ ] Optional: reduce temporary high-volume diagnostic logging after stability window
