# System GRUB Tune

Adds a boot tune to GRUB so the PC speaker plays a short melody during boot. Sets `GRUB_INIT_TUNE` in `/etc/default/grub` and runs `update-grub` only when the line changes.

## Design Notes

The tune is a hardcoded sequence in GRUB's beep syntax (frequency + duration pairs at 1750 Hz base). `update-grub` is only triggered when the config actually changes, keeping the role idempotent. Requires the PC speaker to be present and functional — pairs well with [system-beep](../system-beep) for user-space beep access, though GRUB runs before any user-space configuration.
