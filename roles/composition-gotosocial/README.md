# GoToSocial

[GoToSocial](https://gotosocial.org/) is a lightweight, ActivityPub-compatible Fediverse server. It federates with Mastodon and other ActivityPub implementations, allowing interaction with the broader Fediverse from a self-hosted single-user (or small-group) instance.

## Key Variables

| Variable | Purpose |
|----------|---------|
| `gotosocial_domain` | Public hostname for the instance (default: `gts.awfulwoman.com`) |

## Ports

| Port | Service |
|------|---------|
| `8085` | GoToSocial web UI / API / federation endpoint |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/config.yaml` | Full GoToSocial configuration file |
| `{{ composition_config }}/data` | SQLite database and local media storage |
| `{{ composition_config }}/.cache` | Application cache |

## Notable Configuration (`templates/config.yaml`)

- **Database**: SQLite (WAL mode, 8 MiB cache, 30 min busy timeout) — no external DB required.
- **Storage**: Local filesystem at `/gotosocial/storage`.
- **Registration**: Closed (`accounts-registration-open: false`).
- **Federation mode**: Blocklist (open by default, explicit blocks only).
- **Trusted proxies**: Docker subnets (`172.17/16`, `172.18/16`) and Tailscale (`100.64/10`) — required for correct client IP resolution behind Traefik.
- **Let's Encrypt**: Disabled — TLS handled by Traefik.
- Pinned to `superseriousbusiness/gotosocial:0.21.2`.

## Integrations

- **Traefik**: TLS termination; the container just listens on port 8080 internally. The `traefik.enable=true` label is set but routing rules are managed via Traefik config elsewhere (no explicit router rule in the compose file — configure via Traefik dynamic config or labels as needed).

## Notes

The `host` value in `config.yaml` **must not be changed** after the instance has first run — doing so will break all federated URIs.
