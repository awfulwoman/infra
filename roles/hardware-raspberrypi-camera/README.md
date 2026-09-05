# Raspberry Pi Camera

This role enables the Raspberry Pi camera module. It configures a GStreamer-based H.264 TCP video stream as a systemd service.

The role uses `raspi-config nonint` to enable or disable the camera interface, in an idempotent way. It loads the `bcm2835-v4l2` V4L2 kernel module, installs the GStreamer plugin stack, and installs a systemd service (`raspicam.service`). This service streams 720p30 H.264 video over TCP on port 9000.

The stream uses `tcpserversink` bound to `::0` (all interfaces). As a result, any client that can reach the Pi on port 9000 can receive the raw Matroska/H.264 stream.

## Variables

| Variable | Default | Description |
|---|---|---|
| `CAMERA` | `true` | Whether the camera interface is enabled |

## Notes

- The service runs as the `pi` user. On a host without this user, you must adjust the service file.
- The video bitrate is fixed at 4 Mbps (`video_bitrate=4000000`) in `ExecStartPre`.
- The stream has no authentication and no encryption. Restrict access with firewall rules or Tailscale.
- This role predates the Pi 5 and `libcamera`. It targets the older V4L2/`bcm2835-v4l2` stack. Newer hardware or OS versions can need updates to this role.
