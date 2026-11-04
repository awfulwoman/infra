# RTL-SDR

This role prepares a host for an RTL-SDR USB dongle (Realtek RTL2832U, `0bda:2838`). It is the base for roles that use the dongle, for example `hardware-rtl-433`.

The role:

1. Installs the `rtl-sdr` package. This gives you `rtl_test`, `rtl_power`, `rtl_fm` and related tools.
2. Blacklists the kernel DVB drivers (`dvb_usb_rtl28xxu`, `rtl2832`, `rtl2832_sdr`, `rtl2830`) in `/etc/modprobe.d/blacklist-rtl-sdr.conf`. Without this, the kernel claims the dongle as a TV tuner and userspace tools fail with `usb_claim_interface error -6`.
3. Unloads those modules at once, if they are loaded.
4. Deploys a udev rule. This rule gives the dongle world-read and world-write access, and adds a `/dev/rtl_sdr` symlink.

## Notes

- Only one process can own the dongle at a time. Roles that depend on this role must not run at the same time on one dongle.
- If the dongle is busy, the module unload fails and is ignored. Unplug the dongle, or reboot, to finish the change.
- The udev rule matches `idProduct` `2838`. Other RTL-SDR variants need a different ID.
- Check the dongle with `rtl_test -t`.
