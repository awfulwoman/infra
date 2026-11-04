# RTL-SDR

This role prepares a host for an RTL-SDR USB dongle (Realtek RTL2832U, `0bda:2838`) and sets what the dongle is used for. Only one process can own a dongle at a time, so the role has one mode variable, `rtl_sdr_mode`. The playbook sets it.

## Base setup (all modes)

1. Installs the `rtl-sdr` package. This gives you `rtl_test`, `rtl_power`, `rtl_fm` and related tools.
2. Blacklists the kernel DVB drivers (`dvb_usb_rtl28xxu`, `rtl2832`, `rtl2832_sdr`, `rtl2830`) in `/etc/modprobe.d/blacklist-rtl-sdr.conf`. Without this, the kernel claims the dongle as a TV tuner and userspace tools fail with `usb_claim_interface error -6`.
3. Unloads those modules at once, if they are loaded.
4. Deploys a udev rule. This rule gives the dongle world-read and world-write access, and adds a `/dev/rtl_sdr` symlink.

## Modes

Set `rtl_sdr_mode` on the role in the playbook:

```yaml
- role: hardware-rtl-sdr
  vars: {rtl_sdr_mode: rtl_433}
  tags: [hardware, hardware-rtl-sdr]
```

| Mode | Effect |
|---|---|
| `none` (default) | Base setup only. The role stops and disables `rtl_433` if it is present. |
| `openwebrx` | Same host setup as `none`. The `composition-openwebrx` container uses the dongle. Add `openwebrx` to the host's `compositions:` list. |
| `rtl_433` | Installs [rtl_433](https://github.com/merbanan/rtl_433), which decodes 433 MHz ISM band sensors (temperature sensors, weather stations, doorbells). It publishes events to MQTT. |

Any other value fails the role.

### rtl_433 mode

The role:

1. Installs `rtl-433` from apt.
2. Creates `/etc/rtl_433/service.conf` (templated), which configures JSON output and MQTT publishing.
3. Installs and enables a systemd service. The service runs `rtl_433 -c /etc/rtl_433/service.conf` and restarts on failure, with a 30-second back-off.
4. Restarts the service when the config or the unit file changes.

The role publishes events to `rtl_433/<model>/<id>` on the MQTT broker at `mqtt.{{ domainname_infra }}`, with retain disabled. You must set the `domainname_infra` variable, typically in `group_vars`.

View the logs with `journalctl -u rtl_433 -f -o cat`.

## Notes

- If the dongle is busy, the module unload fails and is ignored. Unplug the dongle, or reboot, to finish the change.
- The udev rule matches `idProduct` `2838`. Other RTL-SDR variants need a different ID.
- Check the dongle with `rtl_test`. Do not run it while a mode is using the dongle.
