# Music Assistant

[Music Assistant](https://music-assistant.io) is a self-hosted music library manager and streaming server that integrates with a wide range of music sources (Spotify, YouTube Music, local files, etc.) and players (Sonos, Chromecast, AirPlay, etc.). It provides a modern web UI and integrates with Home Assistant.

The container runs with `network_mode: host` — this is required for Music Assistant to correctly discover and communicate with players on the local network. It is also given `SYS_ADMIN` and `DAC_READ_SEARCH` capabilities with `apparmor:unconfined` to support mounting SMB shares within the container for library access.

The music library is mounted from `/slowpool/shared/media/music`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}` | Music Assistant data and configuration |
| `/slowpool/shared/media/music` | Music library (mounted at `/media`) |

## Integration

Pairs with the Music Assistant integration in Home Assistant. The HA integration connects to the MA server over the host network.

## DNS

Registers subdomain: `musicassistant`
