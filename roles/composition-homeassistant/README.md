# Home Assistant

Home Assistant is the central home automation platform, providing device integrations, automations, dashboards, and energy monitoring. This role deploys both Home Assistant and ESPHome in a single composition, as ESPHome is tightly coupled to HA for managing ESP-based embedded devices.

Both containers run with `network_mode: host` and `privileged: true` to support Bluetooth, mDNS discovery, and direct hardware access. The D-Bus socket is mounted read-only to enable Bluetooth device communication. The `bluez` apt package is installed on the host for the same reason.

The role also manages several HA configuration files (`configuration.yaml`, `secrets.yaml`, `template.yaml`, `input_select.yaml`) which are templated from `templates/ha/`. Changes to these files trigger a handler to restart HA.

## Key integrations

- **MQTT**: HA configuration includes MQTT-based server power control (WoL + suspend via MQTT topic `servers/<hostname>`)
- **Traefik**: Both services expose themselves via Traefik labels (subdomains: `homeassistant`, `ha`, `esphome`)
- **ESPHome**: Config directory is shared at `{{ composition_config }}/esphome`
- **Powercalc**: The `powercalc` integration is enabled in `configuration.yaml`

## Ports

Both services use host networking — HA listens on `8123`, ESPHome on `6052`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/homeassistant` | HA configuration |
| `{{ composition_config }}/esphome` | ESPHome device configs |
| `{{ composition_config }}/media` | HA media files |
| `/var/run/dbus` | Bluetooth D-Bus (read-only) |
