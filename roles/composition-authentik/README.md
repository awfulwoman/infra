# composition-authentik

[authentik](https://github.com/goauthentik/authentik): self-hosted identity provider (OIDC, SAML, LDAP, forward-auth proxy).

Endpoint: `https://authentik.<domainname_infra>/`

## Variables

| Variable | Purpose |
| --- | --- |
| `vault_composition_authentik_secret_key` | `AUTHENTIK_SECRET_KEY`. Do not rotate: it breaks stored data |
| `vault_composition_authentik_db_password` | Postgres password |

Image tags are pinned in `templates/docker-compose.yaml.j2` (not in variables) so Renovate can update them. Server and worker share a tag: bump both together. Postgres stays on 16 until a planned major upgrade.

## Data

All under `composition_config`: `postgres/`, `data/`, `certs/`, `custom-templates/`. ZFS policy: `critical` (every login and app link depends on it).

## OIDC apps

Apps are declared once in `inventory/group_vars/infra/authentik.yaml` (`authentik_oidc_apps`, keyed by slug). `templates/blueprint-oidc-apps.yaml.j2` turns each entry into an OAuth2 provider and application. The app's own role reads the same entry for its client id (the slug), secret and issuer (`{{ authentik_url }}/application/o/<slug>/`). Do not edit these objects in the UI; the next blueprint apply overwrites them.

To add an app: add an entry, add `vault_composition_authentik_<slug>_client_secret`, deploy authentik, then template the app's own config.

## Notes

- Redis is gone upstream (2026.x), so there is no Redis sidecar.
- The worker mounts the Docker socket and runs as root, per upstream, for outpost auto-deploy.
- First run: open `/if/flow/initial-setup/` to set the `akadmin` password.
- Postgres dir is owned by uid 70 (postgres:alpine).
