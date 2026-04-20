# System Beep

Installs the `beep` package and configures the PC speaker so non-root users can use it. The role installs a udev rule that grants write access to the PC speaker input device to a dedicated `beep` group, then adds the Ansible user to that group.

## Design Notes

Linux requires elevated privileges to write to the PC speaker. Rather than running beep as root, the udev rule (`70-pcspkr-beep.rules`) uses `setfacl` to grant group-level write access whenever the PC Speaker input device is added. This avoids the security footgun of passwordless sudo for beep.

## Included Tunes

The `files/tunes/` directory contains shell scripts using `beep` to play tunes (alarm, Imperial March, Mario victory fanfare, phaser, ring). These are not deployed by the role — they're available for manual use or inclusion in other scripts.
