# Home Assistant

Home Assistant is the central home automation platform, providing device integrations, automations, dashboards, and energy monitoring.

Runs with `network_mode: host` and `privileged: true` to support Bluetooth, mDNS discovery, and direct hardware access. The D-Bus socket is mounted read-only to enable Bluetooth device communication. The `bluez` apt package is installed on the host for the same reason.

The role also manages several HA configuration files (`configuration.yaml`, `secrets.yaml`, `template.yaml`, `input_select.yaml`) which are templated from `templates/ha/`. Changes to these files trigger a handler to restart HA.

ESPHome, which manages the ESP-based embedded devices HA talks to, is deployed by the separate [`composition-esphome`](../composition-esphome/README.md) role.

## Key integrations

- **MQTT**: HA configuration includes MQTT-based server power control (WoL + suspend via MQTT topic `servers/<hostname>`)
- **Traefik**: Exposed via Traefik labels (subdomains: `homeassistant`, `ha`)
- **Powercalc**: The `powercalc` integration is enabled in `configuration.yaml`

## Ports

Host networking — HA listens on `8123`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/homeassistant` | HA configuration |
| `{{ composition_config }}/media` | HA media files |
| `/var/run/dbus` | Bluetooth D-Bus (read-only) |
