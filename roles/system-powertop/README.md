# System PowerTOP

Installs PowerTOP and runs it as a one-shot systemd service at boot to automatically apply power-saving tuning to the host.

PowerTOP's `--auto-tune` flag sets all tunables to their best power-saving values. The role runs this flag once, as a `oneshot` systemd service with `RemainAfterExit=true`. This way, the tuning applies once per boot, and no daemon runs continuously.

## Design Notes

- The role has no configuration variables. It is intentionally simple and opinionated.
- The role ships the service file as a static file because there is nothing to parameterize.
- This role suits always-on servers where power draw matters but hard real-time performance does not matter.
