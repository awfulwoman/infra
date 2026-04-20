# Bookmarks

Deploys two complementary self-hosted bookmark managers side-by-side:

- **[Wallabag](https://wallabag.org/)** — a read-it-later service that saves full article content for offline reading, similar to Pocket or Instapaper.
- **[Linkwarden](https://linkwarden.app/)** — a collaborative bookmark manager that archives snapshots of bookmarked pages. Backed by PostgreSQL and Meilisearch for full-text search.

## Ports

| Port | Service |
|------|---------|
| `8163` (localhost only) | Wallabag |
| `3033` (localhost only) | Linkwarden |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/wallabag/data` | Wallabag application data |
| `{{ composition_config }}/wallabag/images` | Wallabag article images |
| `{{ composition_config }}/linkwarden/data` | Linkwarden attachment storage |
| `{{ composition_config }}/linkwarden/pgdata` | PostgreSQL data |
| `{{ composition_config }}/linkwarden/meili_data` | Meilisearch index |

## Integrations

- **Traefik**: Wallabag at `wallabag.{{ domain_name }}`, Linkwarden at `linkwarden.{{ domain_name }}`, both with Let's Encrypt TLS.
- **PostgreSQL 16**: Linkwarden's primary database, with a healthcheck gate before Linkwarden starts.
- **Meilisearch v1.12.8**: Powers full-text search in Linkwarden, also healthcheck-gated.
