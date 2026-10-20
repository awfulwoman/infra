# composition-authentik

[authentik](https://github.com/goauthentik/authentik): self-hosted identity provider (OIDC, SAML, LDAP, forward-auth proxy).

Endpoint: `https://authentik.<domainname_infra>/`

## Variables

| Variable | Purpose |
| --- | --- |
| `composition_authentik_image` | Pinned server image |
| `composition_authentik_postgres_image` | Postgres 16 (upstream default) |
| `vault_composition_authentik_secret_key` | `AUTHENTIK_SECRET_KEY`. Do not rotate: it breaks stored data |
| `vault_composition_authentik_db_password` | Postgres password |

## Data

All under `composition_config`: `postgres/`, `data/`, `certs/`, `custom-templates/`. ZFS policy: `critical` (every login and app link depends on it).

## Notes

- Redis is gone upstream (2026.x), so there is no Redis sidecar.
- The worker mounts the Docker socket and runs as root, per upstream, for outpost auto-deploy.
- First run: open `/if/flow/initial-setup/` to set the `akadmin` password.
- Postgres dir is owned by uid 70 (postgres:alpine).
