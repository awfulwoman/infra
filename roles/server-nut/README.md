# Server NUT

Configures a host as a Network UPS Tools (NUT) server (`netserver` mode). The host communicates directly with a physically attached UPS via USB and exposes UPS state to NUT clients on the network.

## What it does

Installs `nut`, `nut-client`, and `nut-server`, then deploys a complete set of NUT configuration files to `/etc/nut/`:

- **`nut.conf`** — Sets `MODE=netserver`.
- **`ups.conf`** — Configures the locally attached UPS. Currently hardcoded for an Eaton Ellipse ECO connected via USB (`usbhid-ups` driver, vendor `0463`, product `ffff`).
- **`upsd.conf`** — Binds the NUT daemon to `0.0.0.0:3493` to accept connections from clients on the local network.
- **`upsd.users`** — Creates the `admin` user with full `instcmds` and `SET` permissions, used by `upsmon` on both the server and remote clients.
- **`upsmon.conf`** — Configures the server-local `upsmon` process (primary mode) to monitor the local UPS and initiate shutdown on power loss.
- **`upssched.conf`** — Scheduling configuration for NUT event notifications.

Also deploys a UFW application profile (`nut.ufw.profile`) to `/etc/ufw/applications.d/` and restarts UFW, allowing firewall rules to reference NUT by name rather than port number.

## Variables

| Variable | Description |
|---|---|
| `nut_user_password` | Password for the NUT `admin` user. Sourced from vault (`vault_nut_user_password`). |

## Design Notes

UPS hardware details (USB vendor/product IDs, bus) are hardcoded in `ups.conf` for the specific Eaton unit in use. If the UPS is replaced or moves to a different USB bus, the template will need updating. The example templates in `templates/etc-examples/` document the full range of NUT configuration options and serve as a reference when adjustments are needed.
