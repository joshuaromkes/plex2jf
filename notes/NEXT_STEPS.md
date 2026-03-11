# plex2jf - Next Steps

This document outlines the remaining tasks to complete the project.

## Current Status

Most features are implemented and ready for testing. The project has:
- Full-stack application with React frontend and FastAPI backend
- Database-driven configuration (SQLite)
- Complete sync engine for Plex ↔ Jellyfin ↔ Seerr
- Webhook support for Seerr
- Polling support for Plex watchlists

## What's Done ✅

### Backend
- API Clients: PlexClient, JellyfinClient, SeerrClient
- Database Models: ServerConfig, UserMapping, ExternalUser, SyncState
- REST APIs: Servers, Users, Settings, Dashboard, System, Activity
- Sync Engine: Core sync logic with retry support
- Webhook Handler: Seerr webhook processing

### Frontend
- Dashboard with stats and server status
- Servers page with full CRUD and connection testing
- User Mapping page with refresh and create flows
- Settings page with toggles and sliders
- Activity page with filters and pagination
- "Arr-style" dark theme UI

## What Remains 🔄

### 1. Test the Application

Run the application and verify everything works:

```bash
# Build and start with Docker
docker-compose up --build

# Or run locally for development
# Backend
cd /userdata/plex2jf
pip install -r requirements.txt
python -m uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

**Test Checklist:**
- [ ] Access UI at http://localhost:8000
- [ ] Add Plex server with token
- [ ] Add Jellyfin server with API key
- [ ] Add Seerr server with API key
- [ ] Test each server connection
- [ ] Click "Refresh Users" to fetch users
- [ ] Create user mappings
- [ ] Trigger manual sync
- [ ] Check Activity page
- [ ] Modify settings and save

### 2. Write End-to-End Tests (Optional)

Location: `tests/` directory

Add tests for:
- Server add/edit/delete flow
- User mapping creation
- Settings save/load

### 3. Update README.md

Add:
- UI setup instructions
- Screenshots
- Docker deployment guide
- Migration notes from config.yaml

## Quick Start When You Return

1. Start the app:
   ```bash
   docker-compose up --build
   ```

2. Open http://localhost:8000

3. Configure servers in order:
   - Add Plex server (needs token from plex.tv)
   - Add Jellyfin server (needs API key from Jellyfin settings)
   - Add Seerr server (needs API key from Seerr settings)

4. Map users:
   - Click "Refresh Users" button
   - Create mappings linking Plex → Jellyfin → Seerr users

5. Test sync:
   - Add movie to Plex watchlist
   - Wait for poll (or trigger manually)
   - Check Seerr for new request
   - Check Jellyfin for favorite

## Project Structure

```
plex2jf/
├── src/                    # Python backend
│   ├── api/               # API clients (plex, jellyfin, seerr)
│   ├── database/          # SQLAlchemy models
│   ├── routes/            # FastAPI routes
│   ├── services/          # Sync engine, poller
│   └── webhooks/          # Webhook handlers
├── frontend/              # React frontend
│   ├── src/
│   │   ├── pages/        # Dashboard, Servers, Settings, etc.
│   │   ├── components/   # Layout components
│   │   └── services/     # API client
│   └── dist/             # Built frontend (in Docker)
├── docker-compose.yml     # Docker orchestration
├── Dockerfile             # Multi-stage build
└── notes/                 # This and other notes
```

## Key Files to Review

- `src/main.py` - FastAPI app entry point
- `src/services/sync_engine.py` - Core sync logic
- `frontend/src/pages/Servers.tsx` - Server management UI
- `frontend/src/pages/UserMapping.tsx` - User mapping UI
- `docker-compose.yml` - Deployment config

## Troubleshooting

If something doesn't work:
1. Check logs: `docker-compose logs -f`
2. Check API directly: http://localhost:8000/api
3. Verify server credentials are correct
4. Ensure user mappings are created before testing sync