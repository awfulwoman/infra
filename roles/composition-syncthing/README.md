# Syncthing

This role deploys [Syncthing](https://syncthing.net/), a continuous
peer-to-peer file sync daemon. The container runs as the host user
(`PUID`/`PGID`), so synced files stay usable by other compositions that
bind-mount them.

Devices, folders and the web UI login aren't set here.
[`system-syncthing-config`](../system-syncthing-config) sets them centrally
from camina, through this instance's Traefik route and the shared API key.

## Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_syncthing_data_path` | `{{ composition_root }}/data` | Host path mounted at `/var/syncthing` (config + folders). storage overrides it to `/slowpool/charlie/syncthing` |
| `composition_syncthing_api_key` | `vault_syncthing_api_key` | Passed as `STGUIAPIKEY`; shared with `system-syncthing-config` |

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| 8384 (localhost only) | TCP | Web UI and REST API (proxied via Traefik) |
| 22000 | TCP/UDP | Syncthing sync protocol |
| 21027 | UDP | Local peer discovery |

## Volumes

| Path | Purpose |
|---|---|
| `composition_syncthing_data_path` → `/var/syncthing` | Syncthing config and folders |

## Integrations

- **Traefik**: web UI and API at `syncthing-<host_name>.<domain>`
- **DNS**: registers `syncthing-{host}`
- **ZFS**: backup coverage follows the policy on whichever dataset holds
  `composition_syncthing_data_path`
