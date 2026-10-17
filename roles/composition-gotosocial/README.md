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

This composition runs on public01. Only data that must survive goes on the block storage. The rest is on the VM disk and can be rebuilt.

| Path | Where | Purpose |
|------|-------|---------|
| `{{ composition_config }}/config.yaml` | Block storage | Full GoToSocial configuration file |
| `{{ composition_config }}/db` | Block storage (critical) | SQLite database. It holds the account signing keys. |
| `{{ composition_root }}/media/<account id>` | Block storage (critical) | Media of the two local accounts: charlie and the instance actor |
| `gotosocial-media` Docker volume | VM disk | Remote media cache. GoToSocial keeps it for 7 days and fetches it again on demand. |
| `gotosocial-cache` Docker volume | VM disk | Wazero compile cache |

## Notable Configuration (`templates/config.yaml`)

- **Database**: SQLite (WAL mode, 8 MiB cache, 30 min busy timeout) — no external DB required.
- **Storage**: Local filesystem at `/gotosocial/storage`.
- **Registration**: Closed (`accounts-registration-open: false`).
- **Federation mode**: Blocklist (open by default, explicit blocks only).
- **Trusted proxies**: Docker subnets (`172.17/16`, `172.18/16`) and Tailscale (`100.64/10`) — required for correct client IP resolution behind Traefik.
- **Let's Encrypt**: Disabled — TLS handled by Traefik.
- Pinned to `superseriousbusiness/gotosocial:0.22.2`.

## Integrations

- **Traefik**: TLS termination. The container listens on port 8080 internally. The compose file sets the `traefik.enable=true` label but defines no router rule here. Configure routing through Traefik's dynamic config or labels.

## Notes

CAUTION: Do not change the `host` value in `config.yaml` after the first run of the instance. This will break all federated URIs.

## Clean-up after the move from storage to public01

The instance moved from storage to public01 on 2026-10-17. Do these steps when you are sure that the new instance is stable (a few days):

- [ ] On storage, remove the stopped `gotosocial` container and its `/fastpool/compositions/gotosocial` dataset. It holds the old copy of the database.
- [ ] On storage, destroy the snapshot `fastpool/compositions/gotosocial@pre-move-public01`.
- [ ] On public01, destroy the snapshot `fastpool/compositions/gotosocial@pre-split`.
- [ ] On public01, optional: delete the old remote-account folders in `/fastpool/compositions/gotosocial/media/`. Keep only the two local account folders. These are not backed up.
- [ ] On public01, remove the empty `fastpool/sites/gotosocial` dataset.
- [ ] Remove the gotosocial healthcheck for storage.

Do not start the old container on storage. Two live copies with the same signing keys confuse remote servers.
