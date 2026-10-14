# Wiki.js

[Wiki.js](https://github.com/Requarks/wiki) 2.x wiki with a PostgreSQL sidecar.

- Endpoint: `https://wikijs.{{ domainname_infra }}` (Traefik, port 3000)
- Subdomain is `wikijs` because `wiki` belongs to `composition-wiki-site`.
- Has its own auth; the first visit runs the setup wizard (admin account).

## Variables

| Variable | Purpose |
|---|---|
| `composition_wikijs_image` | Floating `2` tag, refreshed on every deploy (3.x is beta upstream) |
| `composition_wikijs_db_image` | PostgreSQL image |
| `vault_composition_wikijs_db_password` | DB password, shared by app and db |

## Data

`{{ composition_config }}/postgres` holds everything (pages, users, config). Content lives in the DB only, so the ZFS policy is `high`.

## Deploy

```bash
ansible-playbook playbooks/hosts/minipc-8gb-camina/core.yaml --tags composition -e target_composition=wikijs
```
