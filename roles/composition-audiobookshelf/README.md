# Audiobookshelf

[Audiobookshelf](https://www.audiobookshelf.org/) is a self-hosted audiobook and podcast server. It streams audiobooks directly from local storage, tracks playback progress per-user, and supports mobile clients. This role deploys a single Audiobookshelf container backed by a shared media path for audiobook files.

## Ports

| Port | Service |
|------|---------|
| `13378` | Audiobookshelf web UI / API |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ shared_media_path }}/audiobooks` | Audiobook library files |
| `{{ composition_config }}/config` | Application config |
| `{{ composition_config }}/metadata` | Metadata cache |

## Integrations

- **Traefik**: Exposed at `audiobookshelf.{{ domainname_infra }}` with Let's Encrypt TLS.
- **network-register-subdomain**: Registers the `audiobookshelf` subdomain automatically.
- **composition-downloads**: The `librofm-downloader` and `libation` containers in that role populate the same `audiobooks` directory this role reads from.
