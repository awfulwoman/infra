# iPlayarr

[iPlayarr](https://github.com/nikorag/iplayarr) is a BBC iPlayer integration for the *arr stack. It enables downloads of BBC iPlayer content, and it bridges Sonarr/Radarr with the `get_iplayer` tool. It exposes an API that arr applications can query like a Usenet or torrent indexer.

## Ports

Internal port `4404`, exposed via Traefik at `iplayarr.<domain>`.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `iplayarr_downloads` | `/fastpool/storage-share` | Root path for completed downloads |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ iplayarr_downloads }}/shows` | Completed show downloads |
| `/fastpool/downloads/iplayer` | In-progress downloads |
| `{{ composition_config }}/cache` | Download cache/metadata |
| `{{ composition_config }}/config` | Application configuration |

## DNS

Registers subdomain: `iplayarr`
