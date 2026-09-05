# Enable Console Blanking

This role installs a one-shot systemd service. The service blanks the Linux virtual console after a configurable idle timeout. This is useful for headless servers with an attached display, because it stops static content from burning into the screen.

The service runs `setterm -blank <timeout>` at boot, through a `oneshot` unit that targets `/dev/console` directly. This is the only reliable way to set console blanking from a systemd service, rather than from an interactive TTY.

## Variables

| Variable | Default | Description |
|---|---|---|
| `blanking_timeout` | `1` | Minutes of inactivity before the console blanks. Set to `0` to disable blanking |

> Note: the role defines `blanking_timeout` in `vars/main.yaml`, not in `defaults/`. As a result, you can override it at the play or host level only if you edit the role first.
