# Plex2JF Implementation Plan

## Overview
A Dockerized Python application that synchronizes watchlists and requests between Plex, Jellyfin, and Seerr.

## Core Features

### 1. Plex Watchlist → Seerr Request
- Poll Plex watchlists for all users
- Automatically create requests in Seerr for new watchlist items
- Requires user mapping (Plex user → Seerr user)

### 2. Plex Watchlist → Jellyfin Favorite
- When item is added to Plex watchlist, favorite it in Jellyfin
- Uses user mapping (Plex user → Jellyfin user)

### 3. Seerr Request → Jellyfin Favorite
- When a request is made in Seerr, favorite the item in Jellyfin
- Uses user mapping (Seerr user → Jellyfin user)

## Technical Architecture

### Project Structure
```
plex2jf/
├── src/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── sync_engine.py       # Core sync logic
│   ├── api_clients/
│   │   ├── __init__.py
│   │   ├── plex_client.py   # Plex API client
│   │   ├── jellyfin_client.py  # Jellyfin API client
│   │   └── seerr_client.py  # Seerr API client
│   └── models/
│       ├── __init__.py
│       └── user_mapping.py  # User mapping models
├── config/
│   └── config.yaml          # Configuration file
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### API Clients

#### Plex Client
- Authentication: Plex token
- Watchlist access: Requires special handling (GraphQL endpoint or RSS feeds)
- Endpoints:
  - Get user watchlists
  - Get media metadata

#### Jellyfin Client
- Authentication: API key
- Endpoints:
  - Favorite/unfavorite items
  - Get user info
  - Search for items

#### Seerr Client
- Authentication: API key
- Endpoints:
  - Get requests
  - Create requests
  - Get user info

### Configuration
```yaml
plex:
  url: "http://plex:32400"
  token: "${PLEX_TOKEN}"

jellyfin:
  url: "http://jellyfin:8096"
  api_key: "${JELLYFIN_API_KEY}"

seerr:
  url: "http://seerr:5055"
  api_key: "${SEERR_API_KEY}"

sync:
  interval_minutes: 5

user_mappings:
  - plex_username: "john"
    jellyfin_username: "john"
    seerr_username: "john"
    seerr_user_id: 1
```

### Sync Engine
1. Poll Plex watchlists for all mapped users
2. Poll Seerr requests for all mapped users
3. Compare with last known state (stored in SQLite)
4. Execute sync actions:
   - New Plex watchlist item → Seerr request + Jellyfin favorite
   - New Seerr request → Jellyfin favorite

### Docker Setup
- Python 3.11 slim base image
- Environment variables for secrets
- Volume for persistent state (SQLite)
- Health check endpoint

## Implementation Phases

### Phase 1: Core Structure
- [ ] Create project structure
- [ ] Set up Docker configuration
- [ ] Create requirements.txt

### Phase 2: API Clients
- [ ] Implement Plex client with watchlist support
- [ ] Implement Jellyfin client
- [ ] Implement Seerr client

### Phase 3: Sync Engine
- [ ] Implement state tracking (SQLite)
- [ ] Implement sync logic
- [ ] Add user mapping support

### Phase 4: Integration
- [ ] Create main.py with scheduling
- [ ] Add configuration management
- [ ] Add logging

### Phase 5: Documentation
- [ ] Update README with setup instructions
- [ ] Add example configuration
- [ ] Document user mapping

## Notes on Plex Watchlist
Plex watchlists require special handling:
- Option 1: GraphQL endpoint (undocumented but works)
- Option 2: RSS feeds from plex.tv
- Option 3: Web socket monitoring

Will implement Option 1 (GraphQL) as it's most reliable for programmatic access.
