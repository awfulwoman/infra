# Intel MacBook Hardware

Configures WiFi on an Intel MacBook running Ubuntu by installing the correct Broadcom driver and resolving kernel module conflicts.

Ubuntu does not ship the proprietary `wl` (bcmwl) driver by default, and several conflicting open-source Broadcom modules (`b43`, `ssb`, `brcmfmac`, `brcmsmac`, `bcma`) prevent it from loading. This role:

1. Installs `bcmwl-kernel-source` (the proprietary Broadcom driver DKMS package) and `acpi`.
2. Removes all conflicting modules from the running kernel.
3. Loads `wl` and marks it persistent across reboots.

## Notes

- This role targets Intel MacBooks repurposed as Linux servers/desktops. It is not needed for Apple Silicon or non-Apple hardware.
- The `modprobe` tasks take effect immediately without a reboot, though the persistent state is written to `/etc/modprobe.d/`.
