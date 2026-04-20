# MQTT (Mosquitto)

Deploys [Eclipse Mosquitto](https://mosquitto.org), a lightweight MQTT message broker. MQTT is used as the messaging backbone for home automation — Home Assistant, OwnTracks, ESPHome devices, and `linux2mqtt` agents all publish and subscribe through this broker.

The broker is configured with both a standard TCP listener on port `1883` and a WebSocket listener on port `9001`. Anonymous access is enabled. Persistence is on, with data stored at `/mosquitto/data/` and logs at `/mosquitto/log/`.

## Ports

| Port | Purpose |
|------|---------|
| `1883` | MQTT TCP (bound to `0.0.0.0`) |
| `9001` | MQTT WebSocket |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/mosquitto.conf` | Broker configuration |
| `{{ composition_config }}/data` | Persistent message store |
| `{{ composition_config }}/log` | Log files |

## Integrations

- **Home Assistant**: Subscribes for device telemetry and publishes commands (e.g., server suspend via `servers/<hostname>` topic)
- **OwnTracks**: Publishes location data on `owntracks/#` topic
- **linux2mqtt**: Publishes host system metrics
- **ESPHome**: Device telemetry

## DNS

Registers subdomain: `mqtt`
