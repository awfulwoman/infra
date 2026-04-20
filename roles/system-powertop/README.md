# System PowerTOP

Installs PowerTOP and runs it as a one-shot systemd service at boot to automatically apply power-saving tuning to the host.

PowerTOP's `--auto-tune` flag sets all tunables to their optimal power-saving values. Running it as a `oneshot` systemd service with `RemainAfterExit=true` means the tuning is applied once per boot and remains in effect — without a persistent daemon.

## Design Notes

- No configuration variables; the role is intentionally simple and opinionated.
- The service file is shipped as a static file since there is nothing to parameterise.
- Suitable for always-on servers where power draw matters but hard real-time performance is not a concern.
