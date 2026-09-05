# ESPHome

ESPHome manages the ESP-based embedded devices around the home: IR blasters, sensors, displays, and a projector controller. It was previously bundled into `composition-homeassistant`, because it is tightly coupled to HA. It now runs as its own composition, so its device configs, secrets, and static assets (fonts, C++ includes) can be managed on their own.

The role runs with `network_mode: host` and `privileged: true`, for mDNS discovery and direct hardware access during compilation and flashing.

## Device configs

Device YAML files live in `templates/esphome/` and deploy as-is, aside from secret substitution, to `{{ composition_config }}/esphome/`. Most devices import shared boilerplate as **local** ESPHome packages:

```yaml
packages:
  esphome: !include packages/esphome.yaml
  wifi: !include packages/wifi.yaml
  ota: !include packages/ota.yaml
  api: !include packages/api.yaml
```

These packages live in `templates/esphome/packages/` and deploy alongside the device configs, to `{{ composition_config }}/esphome/packages/`, so the `!include` paths resolve inside the container's `/config` mount. This used to be a separately published top-level `esphome/` directory, which outside devices could pull through a `remote_package:` GitHub URL fetch. That mechanism is retired now, because this role manages every known device. Everything now deploys from this role, and only from this role.

`packages/buzzer.yaml`, the RTTTL tunes, is specific to the device fleet, not shared ESPHome boilerplate, but it deploys the same way.

`device-controller-projector.yaml` is fully self-contained, with no shared packages. It was written directly in the ESPHome dashboard and carries its own inline `api`/`ota` credentials, still vaulted here (`vault_esphome_projector_api_key`, `vault_esphome_projector_ota_password`). Its RS-232 protocol is documented in [`VIEWSONIC-PROJECTOR-COMMANDS.md`](VIEWSONIC-PROJECTOR-COMMANDS.md).

### Authoring a new device

For a new device config, set these substitutions and import whichever packages the device needs:

```yaml
substitutions:
  secret_api_key: !secret api_key
  secret_ota_password: !secret ota_password
  secret_wifi_ssid: !secret wifi_ssid
  secret_wifi_password: !secret wifi_password
  secret_wifi_domain: !secret wifi_domain
  name: "device-some-name"
  friendly_name: "Human Readable Name"
  comment: "What this device does"
  area: "Living Room"
  board: "nodemcu-32s"

packages:
  esphome: !include packages/esphome.yaml
  logger: !include packages/logger.yaml
  api: !include packages/api.yaml
  ota: !include packages/ota.yaml
  wifi: !include packages/wifi.yaml
```

Packages cannot see Ansible substitutions directly. They can see only `!secret`, which is why `secrets.yaml` exists as the bridge between vaulted Ansible variables and ESPHome's own config format.

## Secrets

`templates/esphome/secrets.yaml` is templated from Ansible Vault variables and mounted alongside the device configs. ESPHome packages can reference only `!secret`, not Ansible substitutions directly:

| Secret | Vault variable |
|---|---|
| `wifi_ssid` | `vault_homenetwork_ssid_24ghz` (`group_vars/infra/vault_home_wifi.yaml`) — the 2.4GHz-only SSID, since these are all ESP32/ESP8266 boards |
| `wifi_password` | `vault_homenetwork_password` (same file, shared with the main home network) |
| `api_key` | `vault_esphome_api_key` |
| `ota_password` | `vault_esphome_ota_password` |
| `ap_password` | `vault_esphome_ap_password` |
| `wifi_domain` | `composition_esphome_wifi_domain` default. Not a secret, a legacy internal search domain, also referenced in `host_vars/router-4gb-bertha/core.yaml`. |

## Static assets

Every deployed file is an Ansible template (`ansible.builtin.template`), except the two `.ttf` fonts, which use plain `ansible.builtin.copy`. Ansible's `template` module decodes files as UTF-8 and runs them through Jinja2. This is fine for the YAML and C++ files here, because none contain `{{`/`{%`, but it is unsafe for binary content, and upstream Ansible deprecated this use and will remove it in ansible-core 2.23.

- `fonts/pixelmix.ttf` and `fonts/pixelmix_bold.ttf` — used by the LED matrix display on `device-display-charlie-work`
- `uart_read_line_sensor.h` — a custom UART line-reader component, included by `device-controller-projector`
- `viewsonic_projector.h` — not used by any device config today, with content identical to `uart_read_line_sensor.h`. It stays because it existed on the server already. It is a candidate for removal.

## Ports

Host networking — dashboard listens on `6052`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/esphome` | ESPHome device configs, secrets, packages, fonts, includes |
| `/etc/localtime` | Timezone (read-only) |
