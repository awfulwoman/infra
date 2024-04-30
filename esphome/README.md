# esphome

A bunch of defaults for my esphome devices.

Import into each project using:

```yaml
packages:
  remote_package:
    url: http://github.com/whalecoiner/home
    ref: main
    refresh: 5min
    files:
      - esphome/packages/esphome.yaml
      - esphome/packages/ethernet.yaml
      - esphome/packages/logger.yaml
      - esphome/packages/ota.yaml
      - esphome/packages/api.yaml
      - etc
```

Ensure the following values are set in the host yaml (because secrets can't be used inside imported code):

```yaml
substitutions:
  secret_api_key: !secret api_key
  secret_ota_password: !secret ota_password
```