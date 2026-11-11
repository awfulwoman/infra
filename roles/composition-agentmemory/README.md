# agentmemory

[agentmemory](https://github.com/rohitg00/agentmemory): persistent memory for coding agents (MCP and REST).

- REST API: `https://agentmemory.{{ domainname_infra }}` (Traefik, port 3111)
- Viewer: `https://agentmemory-viewer.{{ domainname_infra }}` (port 3113; asks for the bearer token)
- Both need `Authorization: Bearer <secret>`.

## Variables

| Variable | Purpose |
|---|---|
| `vault_composition_agentmemory_secret` | `AGENTMEMORY_SECRET`, the bearer token |

## Decisions

- Image is the upstream prebuilt `ghumarerohit/agentmemory` (amd64 and arm64), pinned inline for Renovate. No LLM or embedding provider is set: keyless BM25 search, no session content leaves the host. Add `EMBEDDING_PROVIDER` / `AGENTMEMORY_LLM_PROVIDER` to `environment_vars.j2` to change this.
- The container starts as root, chowns `/data`, then drops to `node`.
- The first start downloads the `state` and `http` workers from the iii registry, so it needs network and about a minute (`start_period: 90s`).

## Data

`{{ composition_config }}/data` holds memories and state. ZFS policy `high`.

## Deploy

```bash
ansible-playbook playbooks/hosts/minipc-8gb-camina/core.yaml --tags composition -e target_composition=agentmemory
```
