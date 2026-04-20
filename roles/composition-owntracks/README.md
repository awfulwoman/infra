# OwnTracks

[OwnTracks](https://owntracks.org) is a self-hosted location tracking system. Mobile apps (iOS/Android) publish GPS location updates over MQTT, and this composition provides the recorder (which stores and serves the data) and a web frontend for viewing location history on a map.

The recorder connects to the MQTT broker at `mqtt.<domain>` and subscribes to the `owntracks/#` topic. Location history is stored persistently in `{{ composition_config }}/store`.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `owntracks-recorder` | `127.0.0.1:8083` | HTTP API + data storage |
| `owntracks-frontend` | `127.0.0.1:9754` | Map web UI |

Both are exposed via Traefik at `owntracks-recorder.<domain>` and `owntracks.<domain>` respectively.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/config` | Recorder configuration (`recorder.conf`) |
| `{{ composition_config }}/store` | Location history data |

## Integration

- **MQTT**: The recorder connects to the `composition-mqtt` broker. The MQTT host is templated into `recorder.conf` as `mqtt.<domain>`.
- **Home Assistant**: HA has a native OwnTracks integration that can also subscribe to the same MQTT topics.

## DNS

Registers subdomains: `owntracks-recorder`, `owntracks`
