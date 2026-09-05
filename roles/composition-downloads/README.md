# Downloads

The full *arr media automation stack, with all torrent traffic routed through a Mullvad WireGuard VPN through [Gluetun](https://github.com/qdm12/gluetun). Downloads land in a shared media path, which Jellyfin and Audiobookshelf read from.

## Services

| Container | Purpose | Port |
|-----------|---------|------|
| **Gluetun** | WireGuard VPN gateway (Mullvad, Zurich) | `8000` (control API) |
| **qBittorrent** | Torrent client with VueTorrent UI | `8080` (via Gluetun) |
| **Transmission** | Secondary torrent client | `9091` (via Gluetun) |
| **Prowlarr** | Indexer aggregator for all *arr apps | `9696` |
| **Radarr** | Movie collection manager | `7878` |
| **Sonarr** | TV series collection manager | `8989` |
| **Lidarr** | Music collection manager | `8686` |
| **Bazarr** | Subtitle manager for Radarr/Sonarr | `6767` |
| **Jellyseerr** | Media request portal | `5055` |
| **librofm-downloader** | Syncs purchases from Libro.fm as M4B audiobooks | `13377` |

## VPN

qBittorrent and Transmission run with `network_mode: service:gluetun`. All their traffic exits through Mullvad WireGuard. Radarr, Sonarr, and Lidarr wait for Gluetun to become healthy before they start.

VPN credentials are vault-encrypted:

| Variable | Purpose |
|----------|---------|
| `vault_mullvad_wireguard_private_key` | WireGuard private key |
| `vault_mullvad_wireguard_ipaddress` | WireGuard assigned IPv4 address |

The server is pinned to `SERVER_CITIES=zurich, SERVER_COUNTRIES=switzerland`.

## Key Volumes

All media services share `{{ shared_media_path }}`, mounted at `/data`, with the standard Servarr folder layout (`/data/downloads/torrents` and similar paths).

## qBittorrent Lock File Cleanup

qBittorrent writes three files on startup that serve no purpose in a container. Docker already guarantees single-instance enforcement, and a headless setup never uses the IPC socket that passes magnet links to a running instance:

| File | Purpose |
|------|---------|
| `lockfile` | PID-based single-instance guard |
| `ipc-socket` | Unix socket for passing magnet URIs to a running instance |
| `qBittorrent-data.conf.lock` | Qt config file write lock |

These files live in the config volume and survive container restarts. After an unclean shutdown, the stale PID or socket makes every later qbittorrent-nox startup detect a "running" instance and exit immediately, which produces a 502 from Traefik.

The role deploys a `custom-cont-init.d` script (`templates/qbittorrent-remove-locks.sh`) and mounts it at `/custom-cont-init.d/remove-locks.sh`. LSIO containers run scripts from this directory before s6 starts any services, so the lock files are always clear before qbittorrent-nox launches.

## Integrations

- **Traefik**: Exposes each service at its own subdomain on `{{ domainname_infra }}`, with Let's Encrypt TLS.
- **Audiobookshelf** (`composition-audiobookshelf`): Reads from `{{ shared_media_path }}/audiobooks`, which librofm-downloader writes to.
- **Jellyfin**: Shares the same `{{ shared_media_path }}` for movies, TV, and music.
