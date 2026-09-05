# Intel MacBook Hardware

This role configures WiFi on an Intel MacBook that runs Ubuntu. It installs the correct Broadcom driver and removes kernel module conflicts.

Ubuntu does not install the proprietary `wl` (bcmwl) driver by default. Several conflicting open-source Broadcom modules (`b43`, `ssb`, `brcmfmac`, `brcmsmac`, `bcma`) stop it from loading. This role:

1. Installs `bcmwl-kernel-source` (the proprietary Broadcom driver DKMS package) and `acpi`.
2. Removes all conflicting modules from the running kernel.
3. Loads `wl` and sets it to persist across reboots.

## Notes

- This role targets Intel MacBooks that you repurpose as Linux servers or desktops. It is not necessary for Apple Silicon or non-Apple hardware.
- The `modprobe` tasks take effect at once, with no reboot needed. The role writes the persistent state to `/etc/modprobe.d/`.
