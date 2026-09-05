# System Beep

Installs the `beep` package and configures the PC speaker so non-root users can use it. The role installs a udev rule that grants write access to the PC speaker input device to a dedicated `beep` group, then adds the Ansible user to that group.

## Design Notes

Linux needs elevated privileges to write to the PC speaker. Rather than run beep as root, the udev rule (`70-pcspkr-beep.rules`) uses `setfacl` to grant group-level write access whenever the PC Speaker input device is added. This avoids the security risk of passwordless sudo for beep.

## Included Tunes

The `files/tunes/` directory contains shell scripts that use `beep` to play tunes: alarm, Imperial March, Mario victory fanfare, phaser, and ring. The role does not deploy these. They are available for manual use, or for inclusion in other scripts.
