# Home Assistant

Home Assistant is the central home-automation platform. It provides device integrations, automations, dashboards, and energy monitoring.

The container runs with `network_mode: host` and `privileged: true`, to support Bluetooth, mDNS discovery, and direct hardware access. The role mounts the D-Bus socket read-only, to enable Bluetooth device communication. It also installs the `bluez` apt package on the host, for the same reason.

The role also manages several HA configuration files (`configuration.yaml`, `secrets.yaml`, `template.yaml`, `input_select.yaml`), templated from `templates/ha/`, and the automations in `templates/ha/automations/` (see below). A change to any of these files triggers a handler that restarts HA.

The separate [`composition-esphome`](../composition-esphome/README.md) role deploys ESPHome, which manages the ESP-based embedded devices that HA talks to.

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

## Automations managed here

`automations.yaml` is written by the HA UI, so infra leaves it alone. Automations that need to
come from this repo (secrets, shared with a service) live in `templates/ha/automations/` and are
loaded with `automation manual: !include_dir_merge_list automations/`, next to
`automation ui: !include automations.yaml`. Edit those in infra, not in the UI.

- `webmention.yaml`: notices from [webmention-server](../composition-webmention-server/README.md)
  (new Webmentions to review, alerts). It is a webhook trigger with `local_only: false`, reached
  through a Nabu Casa cloud webhook. The id is `vault_composition_homeassistant_webmention_webhook_id`.
  Turn the cloud webhook on in Settings > Home Assistant Cloud > Webhooks, put the
  `https://hooks.nabu.casa/...` URL in `vault_composition_webmention_server_ha_webhook_url`, and set
  `composition_homeassistant_webmention_notify` to the phone's notify entity. A change to any
  of these files restarts HA.
