# Guinea Cameras

Streams live video from USB webcams pointed at the guinea pigs, using [uStreamer](https://github.com/pikvm/ustreamer) — a lightweight, high-performance MJPEG/H.264 streamer designed for Raspberry Pi and similar setups.

Two cameras are active; a third (Microsoft LifeCam) is defined but commented out.

## Services

| Container | Device | Port |
|-----------|--------|------|
| `guineacam01` | `usb-SMI_PC_Cam-video-index0` | `18001` |
| `guineacam02` | `usb-USB_Camera_USB_Camera_USB_Camera-video-index0` | `18002` |

Cameras are passed through by stable USB device ID (`/dev/v4l/by-id/...`) rather than `/dev/videoN` to survive device enumeration changes on reboot.

## Integrations

- **Traefik**: `traefik.enable=true` is set on `guineacam01`; routing rules are expected to be configured separately (e.g., via Traefik dynamic config or additional labels).

## Notes

Each container exposes its MJPEG stream on port `8080` internally (mapped to `1800N` on the host). Streams can be consumed directly in a browser or embedded in Home Assistant via a camera card.
