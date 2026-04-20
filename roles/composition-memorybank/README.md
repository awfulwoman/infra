# Memorybank

Memorybank is a personal memory and note-taking application, deployed from images built and published to `ghcr.io/awfulwoman/memorybank-*`. It consists of a backend API service and a frontend web UI.

The backend stores its data in `{{ composition_config }}/db` and media uploads in `{{ composition_config }}/media`. The frontend is the only publicly routed service, exposed via Traefik at `memorybank.<domain>`.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `memorybank_repo_url` | `https://github.com/awfulwoman/memorybank.git` | Source repo (used if building locally) |
| `memorybank_repo_version` | `main` | Branch/tag to use |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/db` | Database files |
| `{{ composition_config }}/media` | Uploaded media |

## DNS

Registers subdomain: `memorybank`
