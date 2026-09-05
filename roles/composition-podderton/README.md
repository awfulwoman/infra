# Podderton

[Podderton](https://github.com/awfulwoman/podderton) grabs podcasts, stores the
episodes locally, and generates custom RSS feeds. There is no web interface for
settings. A single YAML file controls everything.

## Services

| Container | Purpose |
|-----------|---------|
| `podderton-subscriber` | Polls the configured feeds, downloads new episodes, writes a `.updated` signal file |
| `podderton-generator` | Regenerates RSS feeds when signalled and serves HTTP on port `9988` |

## Ports

| Port | Service |
|------|---------|
| `9988` (via Traefik only) | Feed list webpage and generated `*.xml` feeds |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}` | Mounted read-only at `/config`. Holds `feeds.yaml` |
| `{{ composition_podderton_media_path }}` | Mounted at `/podcasts`. Podderton creates `subscriptions/` and `feeds/` underneath |

## Configuration

The role seeds `{{ composition_config }}/feeds.yaml` on first deploy only
(`force: false`). Edit that file on the host to add feeds. The containers
re-read it on their next heartbeat, so a restart is not necessary.

Minimal example:

```yaml
path: /podcasts
subscribe:
  feeds:
    - name: Three Bean Salad
      id: threebeansalad
      url: https://podcast.global.com/show/5234547/episodes/feed
```

The role then serves the default feed at `https://podderton.{{ domainname_infra }}/feeds.xml`.
See the upstream README for custom feeds, filename formats, and schedule options.

## Integrations

- **Traefik**: exposed at `podderton.{{ domainname_infra }}` with Let's Encrypt TLS.

## Notes

The image is based on `python:3.12-slim`, which has no `bash`, `wget`, or
`curl`. So the generator healthcheck uses a Python TCP connect to port `9988`.
It deliberately does not do an HTTP GET. When it renders the index page with
no feeds, upstream `server.py` raises `UnboundLocalError`. As a result, `/`
returns 500 until `feeds.yaml` has at least one feed. The subscriber has no
listening port and therefore no healthcheck.
