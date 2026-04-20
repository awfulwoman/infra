# Gitea

[Gitea](https://gitea.io/) is a self-hosted Git service. This deployment runs Gitea with Actions (CI/CD) and repository indexing enabled. CI jobs are executed by separate runners deployed via `composition-gitea-runners`.

## Ports

| Port | Service |
|------|---------|
| `3000` (localhost only) | Gitea web UI / API |
| `222` | Git over SSH |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/gitea` | All Gitea data (repos, config, DB) |

## Key Variables

| Variable | Purpose |
|----------|---------|
| `gitea_runner_registration` | Runner registration token (`vault_gitea_runner_registration`) — not used by this role directly, but set here for the runners role |

## Integrations

- **Traefik**: Exposed at `gitea.{{ domain_name }}` with Let's Encrypt TLS.
- **composition-gitea-runners**: Act runners register against this instance using the shared `vault_gitea_runner_registration` token. Runners are deployed separately, potentially on different hosts.

## Notes

- `GITEA__actions__ENABLED=true` activates Gitea Actions.
- `GITEA__indexer__REPO_INDEXER_ENABLED=true` enables full-text code search.
- Pinned to `gitea/gitea:1.25`.
