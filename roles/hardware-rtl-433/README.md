# RTL-433

This role installs and configures [rtl_433](https://github.com/merbanan/rtl_433). rtl_433 receives 433 MHz ISM band sensor data (for example temperature sensors, weather stations, and doorbells) from an RTL-SDR USB dongle, and publishes the decoded events to MQTT.

The role:

1. Installs `rtl-433` from apt.
2. Deploys a udev rule. This rule gives the RTL-SDR dongle (Realtek `0bda:2838`) world-read and world-write access, and adds a `/dev/rtl_sdr` symlink.
3. Creates `/etc/rtl_433/service.conf` (templated), which configures JSON output and MQTT publishing.
4. Installs and enables a systemd service. The service runs `rtl_433 -c /etc/rtl_433/service.conf` and restarts on failure, with a 30-second back-off.

## MQTT Output

The role publishes events to `rtl_433/<model>/<id>` on the MQTT broker at `mqtt.{{ domainname_infra }}`, with retain disabled. You must set the `domainname_infra` variable, typically in `group_vars`.

## Notes

- The udev rule targets the common RTL2838 chipset. Other RTL-SDR chipsets need a different `idProduct`.
- The service restarts automatically after a failure, with a 30-second delay. This stops fast crash loops if the dongle is unplugged.
- The role writes logs to the system journal, through syslog. View them with `journalctl -u rtl_433 -f -o cat`.
- Only one rtl_433 process can own the dongle at a time. Do not run more than one instance on the same host.
