# ESPHome

ESPHome manages the ESP-based embedded devices around the home (IR blasters, sensors, displays, a projector controller). It was previously bundled into `composition-homeassistant` since it's tightly coupled to HA, but is split out into its own composition so its device configs, secrets, and static assets (fonts, C++ includes) can be managed independently.

Runs with `network_mode: host` and `privileged: true` for mDNS discovery and direct hardware access during compilation/flashing.

## Device configs

Device YAML files live in `templates/esphome/` and are deployed verbatim (aside from secret substitution) to `{{ composition_config }}/esphome/`. Most devices import shared boilerplate as **local** ESPHome packages:

```yaml
packages:
  esphome: !include packages/esphome.yaml
  wifi: !include packages/wifi.yaml
  ota: !include packages/ota.yaml
  api: !include packages/api.yaml
```

These packages are the same ones published at the top-level [`esphome/packages/`](../../esphome/README.md) in this repo, which remains the source for any device *outside* this Ansible-managed fleet that still pulls them via the `remote_package:` URL mechanism. `packages/buzzer.yaml`, however, is device-fleet-specific (RTTTL tunes) and isn't part of that shared boilerplate, so it's copied as a static file straight into the ESPHome config's `packages/` directory instead.

`device-controller-projector.yaml` is fully self-contained (no shared packages) — it was authored directly in the ESPHome dashboard and carries its own inline `api`/`ota` credentials, which are still vaulted here (`vault_esphome_projector_api_key`, `vault_esphome_projector_ota_password`).

## Secrets

`templates/esphome/secrets.yaml` is templated from Ansible Vault variables and mounted alongside the device configs, since ESPHome packages can't reference Ansible substitutions directly — only `!secret`:

| Secret | Vault variable |
|---|---|
| `wifi_ssid` | `vault_homenetwork_ssid_24ghz` (`group_vars/infra/vault_home_wifi.yaml`) — the 2.4GHz-only SSID, since these are all ESP32/ESP8266 boards |
| `wifi_password` | `vault_homenetwork_password` (same file, shared with the main home network) |
| `api_key` | `vault_esphome_api_key` |
| `ota_password` | `vault_esphome_ota_password` |
| `ap_password` | `vault_esphome_ap_password` |
| `wifi_domain` | `composition_esphome_wifi_domain` default (not a secret — a legacy internal search domain, also referenced in `host_vars/router-4gb-bertha/core.yaml`) |

## Static assets

Every deployed file is an Ansible template (`ansible.builtin.template`) except the two `.ttf` fonts, which are plain `ansible.builtin.copy`. Ansible's `template` module decodes files as UTF-8 and runs them through Jinja2 — fine for the YAML/C++ files here since none contain `{{`/`{%`, but unsafe for binary content (deprecated upstream and due for removal in ansible-core 2.23).

- `fonts/pixelmix.ttf` and `fonts/pixelmix_bold.ttf` — used by `device-display-charlie-work`'s LED matrix display
- `uart_read_line_sensor.h` — custom UART line-reader component, included by `device-controller-projector`
- `viewsonic_projector.h` — currently unused by any device config (identical content to `uart_read_line_sensor.h`); kept as it existed on the server, but a candidate for removal

## Ports

Host networking — dashboard listens on `6052`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/esphome` | ESPHome device configs, secrets, packages, fonts, includes |
| `/etc/localtime` | Timezone (read-only) |
