# Matter Server

[Python Matter Server](https://github.com/home-assistant-libs/python-matter-server) is the official Matter/Thread controller used by Home Assistant. It runs as a WebSocket server that Home Assistant connects to for controlling Matter-compatible smart home devices over Wi-Fi or Thread networks.

The container runs with `network_mode: host` and `apparmor:unconfined` to allow Bluetooth access via D-Bus (required for Matter commissioning). It uses Bluetooth adapter `0` by default.

Traefik labels are present but commented out — this service is intended for internal HA use only, not direct browser access.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}` | Matter device storage and PAA root certificates |
| `/run/dbus` | D-Bus socket for Bluetooth (read-only) |

## Integration

Pairs with Home Assistant's Matter integration. HA connects to this server via WebSocket on the host network.
