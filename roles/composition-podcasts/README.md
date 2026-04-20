# Podcasts (Pinepods)

[Pinepods](https://www.pinepods.online) is a self-hosted podcast manager with a web UI, supporting subscriptions, episode tracking, downloading, and playback. This composition deploys Pinepods backed by PostgreSQL and Valkey (Redis-compatible) for sessions and caching.

Episode downloads are stored on the slow pool at `/slowpool/shared/media/podcasts`. The PostgreSQL password is stored in Ansible Vault (`vault_pinepods_pg_password`) and the initial admin password in `vault_pinepods_admin_password`.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `pinepods` | `8567:8040` | Web application |
| `db` (PostgreSQL) | `5432` | Primary database |
| `valkey` | `6379` | Session cache |

Pinepods is exposed via Traefik at `podcasts.<domain>`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/pgdata` | PostgreSQL data directory |
| `{{ composition_config }}/backups` | Pinepods backup directory |
| `/slowpool/shared/media/podcasts` | Downloaded episode files |

## DNS

Registers subdomain: `podcasts`
