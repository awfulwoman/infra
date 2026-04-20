# Enable Console Blanking

Installs a one-shot systemd service that blanks the Linux virtual console after a configurable idle timeout. Useful for headless servers with attached displays — prevents static content from burning in the screen.

The service runs `setterm -blank <timeout>` at boot via a `oneshot` unit that targets `/dev/console` directly, which is the only reliable way to set console blanking from a systemd service rather than an interactive TTY.

## Variables

| Variable | Default | Description |
|---|---|---|
| `blanking_timeout` | `1` | Minutes of inactivity before the console blanks. Set to `0` to disable blanking |

> Note: `blanking_timeout` is defined in `vars/main.yaml`, not `defaults/`, so it cannot be overridden at the play/host level without editing the role. Adjust before use if a different timeout is needed.
