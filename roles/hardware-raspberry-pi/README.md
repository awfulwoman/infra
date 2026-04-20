# Raspberry Pi Hardware

Configures Raspberry Pi-specific hardware interfaces and boot settings. Supports both Raspbian (`/boot/config.txt`) and Ubuntu on Pi (`/boot/firmware/usercfg.txt`) by making the boot config path configurable.

The role manages:

- **WiFi / Bluetooth**: Enabled or disabled via `dtoverlay` entries in the boot config.
- **Undervoltage warnings**: Suppresses pemmican brownout warnings when powering via a HAT or non-standard supply.
- **I2C / SPI**: Toggled via `raspi-config nonint` so state is read before applying changes (idempotent).
- **OLED stats display**: Installs Python dependencies (`python3-luma.oled`, `python3-rpi.gpio`, `python3-pil`, `i2c-tools`) and a stats script when both `raspberry_pi_i2c` and `raspberry_pi_oled` are true.
- **Boot config overrides**: Arbitrary lines can be appended to the boot config via `raspberry_pi_config_overrides`.

## Variables

| Variable | Default | Description |
|---|---|---|
| `raspberry_pi_wifi` | `true` | Enable onboard WiFi hardware |
| `raspberry_pi_bluetooth` | `true` | Enable onboard Bluetooth hardware |
| `raspberry_pi_hide_undervoltage_warnings` | `false` | Suppress pemmican brownout warnings (useful with HATs) |
| `raspberry_pi_boot_config_location` | `/boot/config.txt` | Path to boot config; set to `/boot/firmware/usercfg.txt` for Ubuntu |
| `raspberry_pi_i2c` | `false` | Enable I2C interface |
| `raspberry_pi_spi` | `false` | Enable SPI interface |
| `raspberry_pi_oled` | _(undefined)_ | When true alongside `raspberry_pi_i2c`, installs OLED display dependencies |
| `raspberry_pi_config_overrides` | _(undefined)_ | List of extra lines to append to the boot config |

## Notes

- `raspi-config nonint` uses `0` for enabled and `1` for disabled — the inverse of boolean intuition. The role accounts for this.
- WiFi/Bluetooth disable is implemented by adding a `dtoverlay=disable-*` line; enabling removes that line. This avoids leaving conflicting entries.
- The OLED stats script (`oled-stats.py`) is an Adafruit SSD1306 example that displays IP, CPU load, memory, and disk usage on a 128×32 I2C display.
