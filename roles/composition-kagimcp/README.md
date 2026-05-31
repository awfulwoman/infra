# composition-kagimcp

Deploys [kagimcp](https://github.com/kagisearch/kagimcp), the official Kagi MCP server, as a Docker Compose service. It exposes Kagi search and content extraction tools to MCP-compatible clients (Claude Desktop, Claude Code, etc.) over HTTPS via Traefik.

The image is built locally on the server from a bundled `Dockerfile` that installs `kagimcp` from PyPI. The service runs in HTTP/streamable mode — stateless, no volumes required.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_kagimcp_version` | `"1.0.0"` | PyPI version pin; bump to upgrade |
| `composition_kagimcp_subdomains` | `[kagimcp]` | Subdomain(s) registered in DNS |

## Secrets

| Variable | Where |
|----------|-------|
| `vault_kagimcp_kagi_api_key` | `inventory/group_vars/infra/vault_kagi.yaml` |

## DNS

Registers subdomain: `kagimcp`

MCP endpoint: `https://kagimcp.<domain>/mcp`

## Upgrading

Bump `composition_kagimcp_version` in `defaults/main.yaml` and re-run the playbook. The `build: always` flag ensures the image is rebuilt with the new version.
