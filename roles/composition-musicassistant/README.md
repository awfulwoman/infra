# Music Assistant

[Music Assistant](https://music-assistant.io) is a self-hosted music library manager and streaming server. It works with many music sources (for example Spotify, YouTube Music, and local files) and players (for example Sonos, Chromecast, and AirPlay). It provides a modern web UI and integrates with Home Assistant.

The container runs with `network_mode: host`. Music Assistant needs this setting to discover and talk to players on the local network. The container also has `SYS_ADMIN` and `DAC_READ_SEARCH` capabilities with `apparmor:unconfined`, so it can mount SMB shares for library access.

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
