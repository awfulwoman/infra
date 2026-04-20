# Client NUT

Configures a host as a Network UPS Tools (NUT) client (`netclient` mode). The host monitors a remote NUT server and will initiate a clean shutdown if the UPS drops below minimum power thresholds.

## What it does

Installs `nut` and `nut-client`, then deploys two configuration files to `/etc/nut/`:

- **`nut.conf`** — Sets `MODE=netclient`, telling NUT this host is a pure client with no locally attached UPS.
- **`upsmon.conf`** — Configures the remote UPS to monitor. Currently hardcoded to monitor `eaton@192.168.1.130` (the `server-nut` host on the local network). Runs as root, issues `SHUTDOWNCMD "/sbin/shutdown -h"` on power loss, and notifies via syslog, wall, and `upssched`.

## Variables

| Variable | Description |
|---|---|
| `nut_user_password` | Password for the NUT `admin` user. Sourced from vault (`vault_nut_user_password`). |

## Design Notes

The UPS server address (`192.168.1.130`) is currently hardcoded in the `upsmon.conf` template rather than parameterised. This reflects the single-UPS, single-server reality of the home setup — if the NUT server address ever changes, the template needs updating.
