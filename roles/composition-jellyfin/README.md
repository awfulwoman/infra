# Jellyfin

[Jellyfin](https://jellyfin.org) is a free and open-source media server for streaming films, TV shows, music, and photos. It provides a web interface, mobile apps, and smart TV clients, and handles transcoding, metadata fetching, and user management.

Media is served from the shared media path (`{{ shared_media_path }}`), which should be set per-host (typically an NFS or ZFS share).

## Ports

`8096:8096` (also exposed via Traefik at `jellyfin.<domain>` and `jellyfin-vue.<domain>`).

## Key variables

| Variable | Description |
|----------|-------------|
| `shared_media_path` | Path to the media library (set in host/group vars) |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/config` | Jellyfin configuration and database |
| `{{ composition_config }}/cache` | Transcoding cache and image cache |
| `{{ shared_media_path }}` | Media library (mounted at `/data`) |

## DNS

Registers subdomains: `jellyfin`, `jellyfin-vue`
