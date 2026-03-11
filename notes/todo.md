- [x] Configure to automatically create config.yaml if not existant
- [x] Check that the following volume mapping works fine for docker-compose:
      volumes:
      - ./config:/app/config/
  (adjusted from ./config:/app/)
- [x] Add root endpoint to show API info at localhost:8000

**Primary Goal**
instead of a config based setup, I would like a user friendly frontent UI to do the tasks needed of adding the jellyfin server, plex server, api keys, etc
user mapping needs to be done via UI

[] 'arr style UI and UI elements / design & layout following info from ./notes/arrdesign.md
[] build simple UI (proof of concept) for server management & user mapping
[] auto pull all user from plex via api to gather user IDs and names
[] audo pull all users from jellyfin to gather user IDs and names
[] side by side UI to map user A from jellyfin to User B to plex
[]