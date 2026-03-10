# plex2jf

A Python-based Docker service that synchronizes media requests and favorites between Plex, Jellyfin, and Seerr (formerly Jellyseerr).

## Features

- **Seerr → Jellyfin**: When a user requests media in Seerr, automatically favorite it in Jellyfin
- **Plex Watchlist → Seerr**: When a user adds to Plex watchlist, automatically create a Seerr request
- **Plex Watchlist → Jellyfin**: When a user adds to Plex watchlist, automatically favorite it in Jellyfin

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Plex     │     │  Jellyfin   │     │    Seerr    │
│   Server    │     │   Server    │     │   Server    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │  Watchlist        │  Favorites        │  Webhooks
       │  (Poll)           │  (API)            │  (Push)
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

Copy the example config and fill in your values:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

```yaml
plex:
  url: "https://plex.tv"
  token: "YOUR_ADMIN_PLEX_TOKEN"

jellyfin:
  url: "http://jellyfin:8096"
  api_key: "YOUR_JELLYFIN_API_KEY"

seerr:
  url: "http://seerr:5055"
  api_key: "YOUR_SEERR_API_KEY"

user_mappings:
  - plex_username: "john"
    jellyfin_user_id: "abc123"
    seerr_user_id: "1"
```

### 3. Run with Docker Compose

```bash
docker-compose up -d
```

### 4. Configure Seerr Webhook

In Seerr:
1. Go to Settings → Notifications → Webhook
2. Set URL: `http://plex2jf:8000/webhooks/seerr`
3. Enable events: `REQUEST_PENDING`, `REQUEST_APPROVED`

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PLEX2JF_CONFIG_PATH` | `/app/config.yaml` | Path to config file |
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

## How It Works

### Seerr → Jellyfin Sync

1. User requests media in Seerr
2. Seerr sends webhook to plex2jf
3. plex2jf searches Jellyfin for the item by TMDB ID
4. If found, item is favorited for the user
5. If not found, marked as pending (retried later)

### Plex Watchlist → Seerr/Jellyfin

1. plex2jf polls Plex watchlists every 5 minutes
2. New items are extracted with TMDB IDs
3. Items are synced to Seerr (as requests) and/or Jellyfin (as favorites)
4. Sync state is tracked in SQLite database

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

**Webhook not working**
- Verify Seerr webhook URL is correct
- Check plex2jf is on the same network as Seerr
- Check firewall rules

**Plex watchlist not syncing**
- Verify admin token has access to managed users
- Check user mappings are correct
- Review logs for errors

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or pull request.