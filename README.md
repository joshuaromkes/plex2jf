# Plex2JF

A Dockerized Python application that synchronizes watchlists and requests between **Plex**, **Jellyfin**, and **Seerr** (Overseerr/Jellyseerr).

## Features

- **Plex Watchlist → Seerr Request**: When a user adds an item to their Plex watchlist, automatically create a request in Seerr as that user
- **Plex Watchlist → Jellyfin Favorite**: When a user adds an item to their Plex watchlist, automatically favorite it in Jellyfin
- **Seerr Request → Jellyfin Favorite**: When a user makes a request in Seerr, automatically favorite the item in Jellyfin so they see a heart icon

## How It Works

1. **User Mapping**: You configure mappings between Plex, Jellyfin, and Seerr users
2. **Polling**: The application periodically polls for changes in:
   - Plex watchlists (using the GraphQL API)
   - Seerr requests
3. **Syncing**: When new items are detected, the application:
   - Creates Seerr requests for new Plex watchlist items
   - Favorites items in Jellyfin for both Plex watchlist additions and Seerr requests

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Plex Media Server with a Plex Token
- Jellyfin Media Server with an API key
- Seerr (Overseerr or Jellyseerr) with an API key

### 1. Get Your API Credentials

#### Plex Token
1. Sign in to Plex Web App
2. Open browser developer tools (F12)
3. Go to Network tab
4. Refresh the page
5. Look for any request to Plex and find the `X-Plex-Token` header
6. Alternatively, visit: `https://plex.tv/claim` and extract from URL

#### Jellyfin API Key
1. Open Jellyfin Admin Dashboard
2. Go to **Advanced → API Keys**
3. Create a new API key

#### Seerr API Key
1. Open Seerr settings
2. Go to **Settings → General**
3. Copy the API Key

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Plex Configuration
PLEX_URL=http://your-plex-server:32400
PLEX_TOKEN=your_plex_token_here

# Jellyfin Configuration
JELLYFIN_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_jellyfin_api_key_here

# Seerr Configuration
SEERR_URL=http://your-seerr-server:5055
SEERR_API_KEY=your_seerr_api_key_here

# Sync Settings (optional)
SYNC_INTERVAL_MINUTES=5
LOG_LEVEL=INFO
```

### 3. Configure User Mappings

Edit `config/config.yaml` to map your users across services:

```yaml
user_mappings:
  - plex_username: "john_doe"
    jellyfin_username: "john_doe"
    seerr_username: "john_doe"
  
  - plex_username: "jane_doe"
    jellyfin_username: "jane_doe"
    seerr_username: "jane_doe"
```

### 4. Run with Docker Compose

```bash
docker-compose up -d
```

### 5. View Logs

```bash
docker-compose logs -f
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLEX_URL` | No | `http://localhost:32400` | Plex server URL |
| `PLEX_TOKEN` | Yes | - | Plex authentication token |
| `JELLYFIN_URL` | No | `http://localhost:8096` | Jellyfin server URL |
| `JELLYFIN_API_KEY` | Yes | - | Jellyfin API key |
| `SEERR_URL` | No | `http://localhost:5055` | Seerr server URL |
| `SEERR_API_KEY` | Yes | - | Seerr API key |
| `SYNC_INTERVAL_MINUTES` | No | `5` | How often to sync (in minutes) |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### User Mapping Configuration

The `config/config.yaml` file maps users across services:

```yaml
user_mappings:
  - plex_username: "plex_username"
    jellyfin_username: "jellyfin_username"
    jellyfin_user_id: "optional_user_id"
    seerr_username: "seerr_username"
    seerr_user_id: 123  # optional
```

- User IDs are auto-discovered if not provided
- Usernames are case-insensitive

## How Plex Watchlist Access Works

Plex watchlists are accessed via Plex's **GraphQL API** on `discover.provider.plex.tv`. This is the most reliable method for programmatic access to watchlist data.

The application:
1. Authenticates with your Plex token
2. Queries the GraphQL endpoint for watchlist items
3. Extracts metadata (title, year, TMDB ID, etc.)

## Data Persistence

The application stores sync state in `data/sync_state.json`. This tracks:
- Which items have already been synced
- Last sync timestamps

This prevents duplicate requests and allows the app to resume correctly after restarts.

## Troubleshooting

### "No user mappings configured"
- Make sure `config/config.yaml` exists and has valid user mappings
- Check the example in `config/config.yaml`

### "Plex health check failed"
- Verify `PLEX_URL` is correct and accessible
- Check that `PLEX_TOKEN` is valid
- Ensure the Plex server allows remote access

### "Failed to get watchlist"
- The Plex token must belong to a Plex Pass account or the server owner
- Watchlists are associated with Plex accounts, not servers

### Items not being found in Jellyfin
- Make sure the item exists in your Jellyfin library
- The app searches by external IDs (TMDB, TVDB, IMDB) first, then by title/year
- Check Jellyfin has proper metadata with these IDs

## Development

### Running Locally (without Docker)

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables and run:
```bash
export PLEX_TOKEN=your_token
export JELLYFIN_API_KEY=your_key
export SEERR_API_KEY=your_key
python -m src.main
```

### Project Structure

```
plex2jf/
├── src/
│   ├── api_clients/      # API clients for Plex, Jellyfin, Seerr
│   ├── models/           # Data models (UserMapping, MediaItem, etc.)
│   ├── config.py         # Configuration management
│   ├── sync_engine.py    # Core sync logic
│   └── main.py           # Application entry point
├── config/
│   └── config.yaml       # User mappings configuration
├── data/                 # Persistent state storage
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
