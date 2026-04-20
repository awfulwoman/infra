# RTL-433

Installs and configures [rtl_433](https://github.com/merbanan/rtl_433) to receive 433 MHz ISM band sensor data (temperature sensors, weather stations, doorbells, etc.) from an RTL-SDR USB dongle and publish decoded events to MQTT.

The role:

1. Installs `rtl-433` from apt.
2. Deploys a udev rule that grants the RTL-SDR dongle (Realtek `0bda:2838`) world-read/write access and adds a `/dev/rtl_sdr` symlink.
3. Creates `/etc/rtl_433/service.conf` (templated) configuring JSON output and MQTT publishing.
4. Installs and enables a systemd service that runs `rtl_433 -c /etc/rtl_433/service.conf` with automatic restart on failure (30 s back-off).

## MQTT Output

Events are published to `rtl_433/<model>/<id>` on the MQTT broker at `mqtt.{{ domain_name }}` with retain disabled. The `domain_name` variable must be set (typically in `group_vars`).

## Notes

- The udev rule targets the common RTL2838 chipset. Other RTL-SDR chipsets will need a different `idProduct`.
- The service restarts automatically after failures with a 30-second delay, which prevents fast crash loops if the dongle is unplugged.
- Logs are written to the system journal via syslog; view with `journalctl -u rtl_433 -f -o cat`.
- Only one rtl_433 process can own the dongle at a time — do not run multiple instances on the same host.
