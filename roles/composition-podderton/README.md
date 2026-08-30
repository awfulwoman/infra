# Podderton

[Podderton](https://github.com/awfulwoman/podderton) grabs podcasts, stores the
episodes locally, and generates custom RSS feeds. There is no web interface for
settings — everything is driven by a single YAML file.

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
| `{{ composition_config }}` | Mounted read-only at `/config`; holds `feeds.yaml` |
| `{{ composition_podderton_media_path }}` | Mounted at `/podcasts`; Podderton creates `subscriptions/` and `feeds/` underneath |

## Configuration

The role seeds `{{ composition_config }}/feeds.yaml` on first deploy only
(`force: false`). Edit that file on the host to add feeds — the containers
re-read it on their next heartbeat, no restart needed.

Minimal example:

```yaml
path: /podcasts
subscribe:
  feeds:
    - name: Three Bean Salad
      id: threebeansalad
      url: https://podcast.global.com/show/5234547/episodes/feed
```

The default feed is then served at `https://podderton.{{ domainname_infra }}/feeds.xml`.
See the upstream README for custom feeds, filename formats, and schedule options.

## Integrations

- **Traefik**: exposed at `podderton.{{ domainname_infra }}` with Let's Encrypt TLS.

## Notes

The image is `python:3.12-slim` based — no `bash`, `wget`, or `curl` — so the
generator healthcheck is a Python TCP connect to port `9988`. It deliberately
does not do an HTTP GET: upstream `server.py` raises `UnboundLocalError` while
rendering the index page when no feeds are configured, so `/` returns 500 until
`feeds.yaml` has at least one feed. The subscriber has no listening port and
therefore no healthcheck.
