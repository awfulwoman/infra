# kagimcp Composition Design

**Date:** 2026-05-31
**Host:** server-64gb-storage

## Overview

Deploy [kagimcp](https://github.com/kagisearch/kagimcp) — the official Kagi MCP server — as a Docker Compose composition on the storage host, following the existing `composition-*` pattern. The service exposes Kagi search and content extraction tools to MCP-compatible clients (Claude Desktop, Claude Code, etc.) over HTTPS via Traefik.

## Configuration

- **Auth mode:** Single-tenant — `KAGI_API_KEY` stored server-side in Ansible Vault; clients connect without sending a key
- **Network exposure:** Traefik reverse proxy at `kagimcp.<domain>` with TLS via letsencrypt
- **MCP endpoint:** `https://kagimcp.<domain>/mcp`

## Role Structure

```
roles/composition-mcp-kagisearch/
  defaults/main.yaml          # composition_name, version pin, subdomains list
  meta/main.yaml              # dependency: composition-common
  tasks/main.yaml             # template files, DNS registration, compose up
  templates/
    Dockerfile.j2             # python:3.12-slim, pip install kagimcp=={{ version }}
    docker-compose.yaml.j2   # single service with Traefik labels, build: .
    environment_vars.j2      # KAGI_API_KEY from vault
```

### Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_name` | `kagimcp` | Used by composition-common to set paths |
| `composition_mcp_kagisearch_version` | `"1.0.0"` | PyPI version pin; bump to upgrade |
| `composition_mcp_kagisearch_subdomains` | `[kagimcp]` | Subdomain(s) registered in DNS |

## Vault

New vault file: `inventory/host_vars/server-64gb-storage/vault_mcp_kagisearch.yaml`

Contains `vault_mcp_kagisearch_kagi_api_key` encrypted with `ansible-vault encrypt_string`.

## Data Flow

1. Ansible templates `Dockerfile`, `docker-compose.yaml`, `.environment_vars` to `{{ composition_root }}/` on the server
2. `community.docker.docker_compose_v2` with `build: always` builds the image on the server and starts the container
3. Traefik picks up the container's labels and routes `kagimcp.<domain>` → port 8000
4. MCP clients connect to `https://kagimcp.<domain>/mcp` with no per-request auth

## Playbook Change

Add to `playbooks/hosts/server-64gb-storage/core.yaml` in the compositions section:

```yaml
- role: composition-mcp-kagisearch
  tags: [compositions]
```

## Upgrade Path

To upgrade kagimcp: bump `composition_mcp_kagisearch_version` in `defaults/main.yaml` and re-run the playbook. `build: always` ensures the image is rebuilt with the new version.
