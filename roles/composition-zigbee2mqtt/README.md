# Zigbee2MQTT

Deploys [Zigbee2MQTT](https://www.zigbee2mqtt.io/), a bridge that connects a Zigbee USB coordinator to an MQTT broker, enabling direct device interaction without relying on Home Assistant's built-in Zigbee stack. Runs privileged with access to the USB dongle and udev, and exposes a web frontend for device management and monitoring.

## Key variables

| Variable | Default | Description |
|---|---|---|
| `zigbee_usb_device` | `/dev/serial/by-id/usb-Silicon_Labs_Sonoff_Zigbee_3.0_USB_Dongle_Plus_0001-if00-port0` | Host path to the Zigbee USB coordinator |

## Ports

| Port | Purpose |
|---|---|
| 9091 | Web frontend (proxied via Traefik) |

## Volumes

| Path | Purpose |
|---|---|
| `composition_config` | Zigbee2MQTT app data (config, device database) |
| `/run/udev` (read-only) | udev access for USB device enumeration |
| `/etc/localtime` (read-only) | Host timezone |

## Integrations

- **Traefik**: Web UI exposed via HTTPS at `zigbee2mqtt.<domain>` with Let's Encrypt TLS
- **MQTT**: Bridges Zigbee devices to the MQTT broker (broker address configured in Zigbee2MQTT's own `configuration.yaml`)
- **Home Assistant**: Zigbee devices become available in HA via MQTT discovery
- **DNS**: Registers `zigbee2mqtt` subdomain via `network-register-subdomain`
- **Permissions**: Ansible adds `ansible_user` to the `dialout` group for USB serial access
