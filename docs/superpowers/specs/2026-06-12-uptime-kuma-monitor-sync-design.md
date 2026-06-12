# Uptime Kuma Monitor Sync — Design Spec

**Date:** 2026-06-12
**Status:** Approved

## Goal

Automatically populate Uptime Kuma with ICMP ping monitors for every host in the `infra` Ansible group, and HTTPS monitors for every web-facing service on those hosts — all driven by existing inventory data, with no manual UI configuration.

---

## Architecture

Two components:

1. **`uptime-kuma-api` sidecar** — a Python/Flask REST API that runs alongside the existing Uptime Kuma container, bridging Ansible (and any other caller) to Uptime Kuma's internal Socket.io API via the `uptime_kuma_api` Python package. Exposed via Traefik.

2. **Ansible monitor sync task** — added to the `composition-uptime-kuma` role. Runs after the Docker Compose stack is healthy. Builds the desired monitor list from `hostvars` and POSTs it to the sidecar's `/monitors/sync` endpoint.

---

## Source of Truth for HTTP Monitors

The existing `cnames` key in each host's `host_vars/core.yaml` defines all HTTPS-accessible service URLs for that host. It is already maintained for DNS registration via `infra-named`. The uptime-kuma sync uses it directly — adding a CNAME entry automatically creates an HTTP monitor with no additional config.

Format: full domain name using Jinja2 vars, e.g. `jellyfin.{{ domainname_infra }}`.
HTTP monitor URL: `https://{{ cname }}`.

ICMP ping monitors are derived from `host_ipv4` and named with `host_name_short`. All infra hosts get one automatically.

---

## cnames Additions Required

The following `cnames` entries are missing from host_vars and must be added as part of this implementation:

### server-8gb-backups
```yaml
cnames:
  - zfs-api.server-8gb-backups.{{ domainname_infra }}
```

### minipc-8gb-homebrain
Add to existing list:
```yaml
  - owntracks.{{ domainname_infra }}
  - owntracks-recorder.{{ domainname_infra }}
  - zigbee2mqtt.{{ domainname_infra }}
  - zfs-api.minipc-8gb-homebrain.{{ domainname_infra }}
```

### vps-hetzner-public01
```yaml
cnames:
  - zfs-api.vps-hetzner-public01.{{ domainname_infra }}
```

### server-64gb-storage
Add to existing list:
```yaml
  - qbittorrent.{{ domainname_infra }}
  - gluetun.{{ domainname_infra }}
  - bazarr.{{ domainname_infra }}
  - transmission.{{ domainname_infra }}
  - n8n.{{ domainname_infra }}
  - memorybank.{{ domainname_infra }}
  - vikunja.{{ domainname_infra }}
  - uptime-kuma.{{ domainname_infra }}
  - kagimcp.{{ domainname_infra }}
  - firefly.{{ domainname_infra }}
  - firefly-importer.{{ domainname_infra }}
  - zfs.metrics.{{ domainname_infra }}
  - zfs-api.server-64gb-storage.{{ domainname_infra }}
  - jellyfin-vue.{{ domainname_infra }}
  - llmcalc.{{ domainname_infra }}
```

### raspberry-pi4-2gb-deedee
```yaml
cnames:
  - zfs-api.raspberry-pi4-2gb-deedee.{{ domainname_infra }}
```

### raspberry-pi4-4gb-randolph
```yaml
cnames:
  - connect.{{ domainname_infra }}
```

### raspberry-pi5-4gb-belinda
```yaml
cnames:
  - zfs-api.raspberry-pi5-4gb-belinda.{{ domainname_infra }}
```

### No cnames needed
`apple-macmini-m4-16gb-malcolm`, `raspberry-pi4-2gb-pikvm`, `minipc-8gb-test-router`, `raspberry-pi4-8gb-norman` — no compositions, ping-only.

---

## REST API Sidecar

### Stack
- Python 3.11, Flask
- `uptime-kuma-api` PyPI package (Socket.io client)
- Runs as a second service in `composition-uptime-kuma` Docker Compose
- Built from a local Dockerfile in `roles/composition-uptime-kuma/files/api/`

### Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/health` | None | Liveness check |
| `GET` | `/monitors` | API key | List all monitors |
| `POST` | `/monitors` | API key | Create a single monitor |
| `DELETE` | `/monitors/<id>` | API key | Delete by ID |
| `POST` | `/monitors/sync` | API key | Reconcile desired state |

Auth: `X-API-Key` header checked on all endpoints except `/health`.

### `/monitors/sync` behaviour

Accepts a JSON body:
```json
{
  "monitors": [
    {"name": "homebrain", "type": "ping", "hostname": "192.168.1.130"},
    {"name": "jellyfin.ewwww.eu", "type": "http", "url": "https://jellyfin.ewwww.eu"}
  ]
}
```

Logic:
1. Tag all desired monitors `ansible-managed` before creating
2. Fetch all current monitors from Uptime Kuma
3. Split into `ansible-managed` set and `user-managed` set (user-managed are never touched)
4. For each desired monitor: if name already exists in `ansible-managed` set, skip; otherwise create
5. For each existing `ansible-managed` monitor not in desired list: delete
6. Return summary of created/deleted/skipped counts

### Traefik exposure

Exposed at `uptime-kuma-api.{{ domainname_infra }}` via the existing Traefik setup. No public internet access (LAN/Tailscale only, same as all other infra services).

---

## Role Changes (`composition-uptime-kuma`)

### New files
- `files/api/app.py` — Flask application (~150 lines)
- `files/api/requirements.txt` — `flask`, `uptime-kuma-api`
- `files/api/Dockerfile` — `python:3.11-slim`, installs requirements, runs `app.py`

### Modified files
- `templates/docker-compose.yaml.j2` — add `uptime-kuma-api` service with Traefik labels, `depends_on: uptime-kuma`
- `templates/environment_vars.j2` — add `UPTIME_KUMA_URL`, `UPTIME_KUMA_USERNAME`, `UPTIME_KUMA_PASSWORD`, `API_KEY` for the sidecar
- `defaults/main.yaml` — add `composition_uptime_kuma_api_subdomain`, monitor tag name, monitor interval defaults
- `tasks/main.yaml` — add: copy `files/api/` to `composition_root/api/`, wait for `/health`, build monitor list from hostvars, POST to `/monitors/sync`

### Ansible monitor-building logic (in tasks)

```yaml
# Ping monitors — all infra hosts
# HTTP monitors — from each host's cnames list (if defined)
# Desired state posted to: https://uptime-kuma-api.{{ domainname_infra }}/monitors/sync
```

The task iterates `groups['infra']`, reads `hostvars[host]['host_ipv4']`, `hostvars[host]['host_name_short']`, and `hostvars[host].get('cnames', [])`.

---

## New Vault Credentials

Three new vault-encrypted variables added to a new `inventory/group_vars/infra/vault_uptime_kuma.yaml` (following the per-composition vault file pattern already used for n8n, paperless-ngx, etc.):

- `vault_uptime_kuma_username` — Uptime Kuma admin username
- `vault_uptime_kuma_password` — Uptime Kuma admin password
- `vault_uptime_kuma_api_key` — API key for the REST sidecar

Generate with:
```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_uptime_kuma_api_key'
```

---

## What is NOT in scope

- Notification channel configuration (done via UI)
- Monitor status pages (done via UI)
- Push-type monitors
- Removing user-created monitors (the `ansible-managed` tag protects them)
