# GitHub to KaraKeep

Runs [github2karakeep](https://github.com/hasansino/github2karakeep), a background service that syncs GitHub starred repositories into a [KaraKeep](https://karakeep.app/) bookmark list. Starred repos are imported with their topics as tags and grouped under the `github2karakeep` list and tag.

## Key Variables

| Variable | Purpose |
|----------|---------|
| `github2karakeep_gh_token` | GitHub personal access token with read:user scope (`vault_github_stars_token`) |
| `github2karakeep_kk_url` | KaraKeep instance URL (default: `https://karakeep.{{ domain_name }}`) |
| `github2karakeep_kk_token` | KaraKeep API token (`vault_github2karakeep_token`) |
| `github2karakeep_schedule` | Sync schedule (default: `@daily`) |

## Behaviour

- Syncs up to 100 repos per page (`GH_PER_PAGE=100`)
- Extracts GitHub topics as KaraKeep tags (`GH_EXTRACT_TOPICS=true`)
- Exports 10 items per run (`EXPORT_LIMIT=10`)
- Checks every 12 hours (`UPDATE_INTERVAL=12h`)
- All imports tagged `github2karakeep` and added to the `github2karakeep` list
- GitHub username hardcoded to `awfulwoman`

## Integrations

- **KaraKeep** (`composition-karakeep` or equivalent): Requires a running KaraKeep instance and a valid API token.
- No web UI; runs as a background sync daemon with no exposed ports.
