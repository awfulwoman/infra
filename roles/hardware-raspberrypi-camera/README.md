# Raspberry Pi Camera

Enables the Raspberry Pi camera module and sets up a GStreamer-based H.264 TCP video stream as a systemd service.

The role uses `raspi-config nonint` to enable/disable the camera interface idempotently, loads the `bcm2835-v4l2` V4L2 kernel module, installs the GStreamer plugin stack, and installs a systemd service (`raspicam.service`) that streams 720p30 H.264 video over TCP on port 9000.

The stream uses `tcpserversink` bound to `::0` (all interfaces), so any client that can reach the Pi on port 9000 can receive the raw Matroska/H.264 stream.

## Variables

| Variable | Default | Description |
|---|---|---|
| `CAMERA` | `true` | Whether the camera interface should be enabled |

## Notes

- The service runs as the `pi` user — hosts that don't have this user will need the service file adjusted.
- Video bitrate is hardcoded to 4 Mbps (`video_bitrate=4000000`) in `ExecStartPre`.
- The stream is unauthenticated and unencrypted; restrict access via firewall rules or Tailscale.
- This role predates the Pi 5 / `libcamera` era — it targets the legacy V4L2/`bcm2835-v4l2` stack and may need updating for newer hardware or OS versions.
