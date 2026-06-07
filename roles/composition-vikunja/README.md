# Vikunja

[Vikunja](https://vikunja.io/) is a self-hosted task management and to-do app. It supports projects, teams, labels, due dates, and a Kanban board view.

## Ports

| Port | Service |
|------|---------|
| `3456` (internal only) | Vikunja web UI + API |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/files` | Task attachments and project backgrounds |
| `{{ composition_config }}/postgres` | PostgreSQL database data |

## Secrets

| Vault variable | Purpose |
|---|---|
| `vault_vikunja_db_password` | PostgreSQL password (shared by app and db) |
| `vault_vikunja_secret_key` | Session signing secret |

## Integrations

- **Traefik**: Exposed at `vikunja.{{ domainname_infra }}` with Let's Encrypt TLS.
- **PostgreSQL**: Runs as a sidecar (`vikunja_db`) on the same Docker network.
