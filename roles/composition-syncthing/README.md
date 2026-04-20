# Syncthing

Deploys [Syncthing](https://syncthing.net/), a continuous peer-to-peer file synchronisation daemon. The container's hostname is set to the Ansible inventory hostname so that device names in the Syncthing web UI match the host. Data is stored on the ZFS slow pool at `/slowpool/charlie/syncthing`.

## Key variables

| Variable | Default | Description |
|---|---|---|
| `syncthing_paths` | `false` | Reserved for declaring additional sync paths (currently unused) |

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| 8384 (localhost only) | TCP | Web UI (proxied via Traefik) |
| 22000 | TCP/UDP | Syncthing sync protocol |
| 21027 | UDP | Local peer discovery |

## Volumes

| Path | Purpose |
|---|---|
| `/slowpool/charlie/syncthing` | Syncthing config and sync root (ZFS slow pool) |

## Integrations

- **Traefik**: Web UI exposed via HTTPS at `syncthing.<hostname>.<domain>` with Let's Encrypt TLS
- **DNS**: Registers `syncthing.<hostname>` subdomain via `network-register-subdomain`
- **ZFS**: Data lives on the slow-pool ZFS dataset; backup coverage depends on host ZFS policy
