# ha-mcp

[ha-mcp](https://github.com/homeassistant-ai/ha-mcp): MCP server for Home Assistant, run as `ha-mcp-web` (streamable HTTP, port 8086).

- Endpoint: `https://ha-mcp.{{ domainname_infra }}/<secret path>` (Traefik)
- The endpoint has no auth of its own. The secret path is the credential, so keep the URL private.

## Variables

| Variable | Purpose |
|---|---|
| `vault_composition_ha_mcp_secret_path` | `MCP_SECRET_PATH`, e.g. `/private_<random>` (leading slash) |
| `vault_composition_ha_mcp_homeassistant_token` | HA long-lived access token (Profile > Security). Admin user recommended |

```bash
ansible-vault encrypt_string "/private_$(openssl rand -hex 32)" --name 'vault_composition_ha_mcp_secret_path'
```

## Decisions

- Image `ghcr.io/homeassistant-ai/ha-mcp`, pinned inline for Renovate. The image default command is stdio, so compose sets `command: ["ha-mcp-web"]`.
- Non-root (`mcpuser`). Stateless, so ZFS policy `none`.
- No upstream HEALTHCHECK: TCP probe on 8086 with bash.
- HA is reached through its own Traefik name, `https://homeassistant.<domain>`.

## Deploy

```bash
ansible-playbook playbooks/hosts/minipc-8gb-homebrain/core.yaml --tags composition -e target_composition=ha-mcp
```

The DNS label only resolves after the zone is published from bertha:

```bash
ansible-playbook playbooks/hosts/router-4gb-bertha/core.yaml --tags infra-named
```

Clients: opencode on camina, see `roles/system-opencode/README.md`.
