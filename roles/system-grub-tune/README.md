# System GRUB Tune

This role adds a boot tune to GRUB, so the PC speaker plays a short melody
during boot. It sets `GRUB_INIT_TUNE` in `/etc/default/grub`, and runs
`update-grub` only when the line changes.

## Design Notes

The tune is a fixed sequence in GRUB's beep syntax: frequency and duration
pairs at a 1750 Hz base. `update-grub` runs only when the configuration actually
changes, so the role stays idempotent.

This role needs a PC speaker that is present and works. It pairs well with
[system-beep](../system-beep) for user-space beep access, though GRUB runs
before any user-space configuration.
