# Downloads

The full *arr media automation stack, with all torrent traffic routed through a Mullvad WireGuard VPN via [Gluetun](https://github.com/qdm12/gluetun). Downloads land in a shared media path consumed by Jellyfin and Audiobookshelf.

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
| **Libation** | Syncs Audible purchases | — |

## VPN

qBittorrent and Transmission run with `network_mode: service:gluetun` — all their traffic exits through Mullvad WireGuard. Radarr, Sonarr, and Lidarr depend on Gluetun being healthy before starting.

VPN credentials are vault-encrypted:

| Variable | Purpose |
|----------|---------|
| `vault_mullvad_wireguard_private_key` | WireGuard private key |
| `vault_mullvad_wireguard_ipaddress` | WireGuard assigned IPv4 address |

Server is pinned to `SERVER_CITIES=zurich, SERVER_COUNTRIES=switzerland`.

## Key Volumes

All media services share `{{ shared_media_path }}` mounted at `/data`, with the standard Servarr folder layout (`/data/downloads/torrents`, etc.).

## Integrations

- **Traefik**: All services exposed at their respective subdomains on `{{ domain_name }}` with Let's Encrypt TLS.
- **Audiobookshelf** (`composition-audiobookshelf`): Reads from `{{ shared_media_path }}/audiobooks`, which librofm-downloader and Libation write to.
- **Jellyfin**: Shares the same `{{ shared_media_path }}` for movies, TV, and music.
