---
name: infra-health
description: Use when checking if infra hosts are reachable, if compositions are running and healthy, or to identify cnames in host_vars that don't correspond to a running composition on that host.
---

## SSH host aliases

All infra hosts are reachable by short alias (from `~/.ssh/config`):

| Alias | Full name |
|-------|-----------|
| backups | server-8gb-backups |
| homebrain | minipc-8gb-homebrain |
| malcolm | apple-macmini-m4-16gb-malcolm |
| pikvm | raspberry-pi4-2gb-pikvm |
| public01 | vps-hetzner-public01 |
| storage | server-64gb-storage |
| test-router | minipc-8gb-test-router |
| deedee | raspberry-pi4-2gb-deedee |
| randolph | raspberry-pi4-4gb-randolph |
| norman | raspberry-pi4-8gb-norman |
| belinda | raspberry-pi5-4gb-belinda |

## Host reachability

```bash
for host in backups homebrain malcolm pikvm public01 storage test-router deedee randolph norman belinda; do
  ssh -o ConnectTimeout=3 -o BatchMode=yes $host 'echo "$HOSTNAME ok"' 2>/dev/null || echo "$host: UNREACHABLE"
done
```

## Composition health

`docker compose ls` lists all running projects. Project names match `composition_name` in each role's `defaults/main.yaml` — this is the key invariant for cross-referencing.

```bash
# All projects and their status
ssh <host> 'docker compose ls'

# Only unhealthy/non-running containers
ssh <host> 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -Ev "(Up [0-9]+ (second|minute|hour|day)|STATUS)"'

# Logs for a struggling container
ssh <host> 'docker logs <name> --tail 30 2>&1'
```

## Rogue cname detection

A **rogue cname** is an entry in `inventory/host_vars/<host>/core.yaml` under `cnames:` that has no corresponding running composition on that host.

**Steps:**

1. Read the host's `cnames` list from `inventory/host_vars/<host>/core.yaml`
2. Get running project names: `ssh <host> 'docker compose ls --format json | python3 -c "import sys,json;[print(p[\"Name\"]) for p in json.load(sys.stdin)]"'`
3. For each cname, strip `.<domainname_infra>` (e.g. `.ewwww.eu`) to get the subdomain
4. Look up the subdomain in the mapping table below to find the expected composition name
5. Flag any where no matching project is running

**Check both directions:** also flag compositions running on a host that have no cname registered (services with a web UI that are invisible to monitoring).

## Cname → composition name mapping

Most cnames map 1:1 (subdomain = composition_name). Non-obvious exceptions:

| cname subdomain | composition_name | Notes |
|-----------------|-----------------|-------|
| ha | homeassistant | HA alias |
| esphome | homeassistant | ESPHome runs inside HA compose |
| jellyfin-vue | jellyfin | Second frontend for same stack |
| firefly-importer | finances | Same compose project as firefly |
| traefik.* | reverseproxy | Traefik dashboard |
| whoami.* | reverseproxy | Whoami test service |
| home | homepage | |
| lan | watchyourlan | |
| zfs.metrics | victoriametrics | |
| chat | gotosocial | |
| kagimcp | mcp-kagisearch | |
| llmcalc | llm-inference-calculator | |
| connect | 1password-connect | On randolph |
| zfs-api.* | zfs-api | Hostname-scoped subdomain |
| syncthing.* | syncthing | Hostname-scoped subdomain |

## Services that intentionally have no composition

Some cnames point at non-Docker services or external forwarding and will always appear rogue:

- `gateway` — MCP gateway service; source repo is `awfulwoman/gateway`. Only deployed where explicitly included in the host playbook.
- `traefik_providers` entries (homeassistant, esphome, watchyourlan, gateway) are Traefik router config, not separate compose projects
