# Client NUT

This role configures a host as a Network UPS Tools (NUT) client, in `netclient` mode. The host monitors a remote NUT server. If the UPS drops below minimum power thresholds, the host starts a clean shutdown.

## What it does

The role installs `nut` and `nut-client`, then deploys two configuration files to `/etc/nut/`:

- **`nut.conf`** — Sets `MODE=netclient`. This tells NUT that this host is a pure client, with no locally attached UPS.
- **`upsmon.conf`** — Configures the remote UPS to monitor. This is currently hardcoded to monitor `eaton@192.168.1.130`, the `server-nut` host on the local network. It runs as root, issues `SHUTDOWNCMD "/sbin/shutdown -h"` on power loss, and sends notices through syslog, wall, and `upssched`.

## Variables

| Variable | Description |
|---|---|
| `nut_user_password` | Password for the NUT `admin` user. Sourced from vault (`vault_nut_user_password`). |

## Design Notes

The UPS server address (`192.168.1.130`) is hardcoded in the `upsmon.conf` template, not a variable. This matches the single-UPS, single-server home setup. If the NUT server address changes, you must update the template.
