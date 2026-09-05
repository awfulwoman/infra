# GoToSocial

[GoToSocial](https://gotosocial.org/) is a lightweight, ActivityPub-compatible Fediverse server. It federates with Mastodon and other ActivityPub implementations. You can use it to interact with the wider Fediverse from a single-user or small-group instance.

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

- **Traefik**: TLS termination. The container listens on port 8080 internally. The compose file sets the `traefik.enable=true` label but defines no router rule here. Configure routing through Traefik's dynamic config or labels.

## Notes

CAUTION: Do not change the `host` value in `config.yaml` after the first run of the instance. This will break all federated URIs.
