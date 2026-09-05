# Raspberry Pi Hardware

This role configures Raspberry Pi hardware interfaces and boot settings. It works with both Raspbian (`/boot/config.txt`) and Ubuntu on Pi (`/boot/firmware/usercfg.txt`), because the boot config path is a variable.

The role manages:

- **WiFi / Bluetooth**: The role enables or disables these through `dtoverlay` entries in the boot config.
- **Undervoltage warnings**: The role hides pemmican brownout warnings when you power the Pi from a HAT or a non-standard supply.
- **I2C / SPI**: The role toggles these through `raspi-config nonint`. It reads the current state before it applies changes, so the task is idempotent.
- **OLED stats display**: When both `raspberry_pi_i2c` and `raspberry_pi_oled` are true, the role installs Python dependencies (`python3-luma.oled`, `python3-rpi.gpio`, `python3-pil`, `i2c-tools`) and a stats script.
- **Boot config overrides**: You can append extra lines to the boot config through `raspberry_pi_config_overrides`.

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

- `raspi-config nonint` uses `0` for enabled and `1` for disabled. This is the opposite of what you expect from a boolean. The role handles this difference for you.
- To disable WiFi or Bluetooth, the role adds a `dtoverlay=disable-*` line. To enable it, the role removes that line. This stops conflicting entries from building up.
- The OLED stats script (`oled-stats.py`) is an Adafruit SSD1306 example. It shows IP address, CPU load, memory, and disk usage on a 128×32 I2C display.
