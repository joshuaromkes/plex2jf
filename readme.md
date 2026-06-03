# plex2jf

A Python-based Docker service that synchronizes media requests and favorites between Plex, Jellyfin, and Seerr (formerly Jellyseerr).


## AI Disclosure
Before I continue, I would like to disclose the use of AI in the creation of this project.
I am a system administrator NOT a programmer. Though I have extensive experience with building systems, managing them etc.
I do not have professional experience in development, nor do I plan on aqcuiring same.

This project comes with no warranty or guarantee. If you think you can improve this project in any way please feel free to touch base.
Otherwise, I will do my absolute best in terms of maintaining and keeping this project running with the very limited dev experience I have.

## Reason For Project
I am a big fan of plex, and likewise with jellyfin. When migrating my users over from plex to jellyfin I noticed a few limitations
1. Watchlist: there is no surefire way to move their watchlist over from plex to jellyfin
2. Favorites: when someone requests something in seerr, there is no (current) surefire way to auto-favorite these requests into jellyfin



## Features

- **Plex Watchlist → Seerr**: When a user adds to Plex watchlist, automatically create a Seerr request.
- **Seerr → Jellyfin**: When a user requests media in Seerr, plex2jf will favorite it in Jellyfin.
- **Loose Mapping Fallback**: If strict IDs are missing/unusable, Plex items can be resolved via title/year/type search with confidence guardrails.
- **Polling Interval**: Both watchlist and favourites are automatically kept in sync with a set polling interval (default 300s)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Plex     │     │  Jellyfin   │     │    Seerr    │
│   Server    │     │   Server    │     │   Server    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │  Watchlist        │  Favorites        │  Completed Requests
       │  (Poll)           │  (API)            │  (API)
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │   plex2jf   │
                    │   (Docker)  │
                    └─────────────┘
```


## Quick Start

### 1. Get API Credentials

#### Plex Admin Token
1. Open Plex Web
2. Go to Settings → Account
3. Click "View XML" on any item
4. Look for `authToken` in the URL

#### Jellyfin API Key
1. Open Jellyfin Dashboard
2. Go to API Keys
3. Create a new API key

#### Seerr API Key
1. Open Seerr Settings
2. Go to General
3. Copy the API Key

#### User IDs
- **Jellyfin**: Dashboard → Users → Click user → URL contains ID
- **Seerr**: Settings → Users → User list shows IDs

### 2. Create Configuration

Servers - Add Server
- select your service type
- Add name (optional)
- Input URL (http://localhost:port)
- Input Token

Click "Add Server"

### 3. User Mapping

1. User Mapping - Refresh Users
2. Add Mapping
3. Choose your plex user, Jellyfin User, Seerr User - Hit save

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PLEX2JF_CONFIG_PATH` | `/app/config/config.yaml` | Path to config file |
| `PLEX2JF_DB_PATH` | `/data/plex2jf.db` | Path to SQLite database |
| `PLEX2JF_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `PLEX2JF_POLLING_INTERVAL` | `300` | Polling interval in seconds |

### Config File Options

```yaml
# Server connections
plex:
  url: "https://plex.tv"
  token: "YOUR_TOKEN"

jellyfin:
  url: "http://jellyfin:8096"
  api_key: "YOUR_KEY"

seerr:
  url: "http://seerr:5055"
  api_key: "YOUR_KEY"

# Map users between services
user_mappings:
  - plex_username: "john"
    plex_user_id: "123"      # Optional
    jellyfin_user_id: "abc"
    seerr_user_id: "1"

# Sync settings
sync:
  polling_interval: 300      # 5 minutes
  enable_webhooks: true
  webhook_port: 8000
  features:
    seerr_to_jellyfin: true
    plex_watchlist_to_seerr: true
    plex_watchlist_to_jellyfin: true

# Logging
logging:
  level: "INFO"
  file: "/data/plex2jf.log"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Sync statistics |
| `/sync/plex-watchlist` | POST | Manually trigger Plex sync |
| `/sync/retry-pending` | POST | Retry pending items |
| `/webhooks/seerr` | POST | Seerr webhook endpoint |

## Web UI

plex2jf includes a modern web interface for managing servers, user mappings, and monitoring sync statistics.

### Access
After starting the service, open your browser to:
```
http://localhost:8000
```

### Features
- **Dashboard**: Overview of sync statistics and system health.
- **Servers**: Configure Plex, Jellyfin, and Seerr connections with an optional name field and improved spacing.
- **User Mapping**: Table-based interface for mapping users between services with inline editing, searchable dropdowns, and per-mapping statistics.
- **Settings**: Adjust sync preferences and logging levels.
- **Activity**: View recent sync events and logs.

The UI follows an "Arr-style" dark theme and is fully responsive, enhancing usability with clearer layouts and consistent design.

## How It Works

### Seerr → Jellyfin Sync

1. User requests media in Seerr
2. Seerr sends webhook to plex2jf
3. plex2jf searches Jellyfin for the item by TMDB ID
4. If found, item is favorited for the user
5. If not found, marked as pending (retried later)

### Plex Watchlist → Seerr/Jellyfin

1. plex2jf polls Plex watchlists every 5 minutes
2. New items are extracted with external IDs (`tmdb`/`imdb`/`tvdb`) when available
3. Strict ID-first sync is attempted for Seerr requests and/or Jellyfin favorites
4. If strict ID resolution fails, fallback search uses title/year/type with scoring and ambiguity guardrails
5. Unresolved items are tracked in SQLite with retry-safe state so they can be retried later without DB integrity issues

## Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

### Project Structure

```
plex2jf/
├── src/
│   ├── api/           # API clients (Plex, Jellyfin, Seerr)
│   ├── config/        # Configuration management
│   ├── database/      # Database models and session
│   ├── services/      # Sync engine, poller, user mapper
│   ├── webhooks/      # Webhook handlers and routes
│   ├── utils/         # Utilities
│   ├── main.py        # FastAPI app
│   └── scheduler.py   # Background polling scheduler
├── tests/             # Test suite
├── Dockerfile
├── docker-compose.yml
├── config.example.yaml
└── requirements.txt
```

## Troubleshooting

### Check Logs

```bash
docker logs plex2jf
```

### Test API Connections

```bash
# Health check
curl http://localhost:8000/health

# Get stats
curl http://localhost:8000/stats
```

### Common Issues

**Item not found in Jellyfin**
- Item hasn't been downloaded yet
- Will be retried automatically
- Check logs for pending items

**Plex watchlist not syncing**
- Verify admin token has access to managed users
- Check user mappings are correct
- Review logs for errors

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or pull request.
