# esphome

A bunch of defaults for my [ESPHome](https://www.esphome.io/) devices.

Ensure the following values are set in the project yaml (because secrets can't be used inside imported code):

```yaml
substitutions:
  secret_api_key: !secret api_key
  secret_ota_password: !secret ota_password
  secret_wifi_ssid: !secret wifi_ssid
  secret_wifi_password: !secret wifi_password
  secret_ap_password: !secret ap_password
  secret_wifi_domain: !secret wifi_domain
```

Import these base packages:

```yaml
packages:
  remote_package:
    url: http://github.com/awfulwoman/infra
    ref: main
    refresh: 5min
    files:
      - esphome/packages/esphome.yaml
      - esphome/packages/ethernet.yaml
      - esphome/packages/wifi.yaml
      - esphome/packages/logger.yaml
      - esphome/packages/ota.yaml
      - esphome/packages/api.yaml
      - esphome/packages/time.yaml
      - etc
```

Imported values can be overridden as necessary:

```yaml
substitutions:
  name: "project-mcproject"
  friendly_name: "A PROJECT"
  comment: "A COMMENT"
  area: "Living Room"
  platform: esp32
  board: esp32dev
  owner: awfulwowman
  version: "1.0.0"
```
