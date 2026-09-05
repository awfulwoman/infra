# Guinea Cameras

This role streams live video from USB webcams pointed at the guinea pigs. It uses [uStreamer](https://github.com/pikvm/ustreamer), a lightweight MJPEG/H.264 streamer for Raspberry Pi and similar setups.

Two cameras are active now. A third (Microsoft LifeCam) is defined but commented out.

## Services

| Container | Device | Port |
|-----------|--------|------|
| `guineacam01` | `usb-SMI_PC_Cam-video-index0` | `18001` |
| `guineacam02` | `usb-USB_Camera_USB_Camera_USB_Camera-video-index0` | `18002` |

The role passes cameras through by stable USB device ID (`/dev/v4l/by-id/...`), not `/dev/videoN`, so they survive device enumeration changes on reboot.

## Integrations

- **Traefik**: `traefik.enable=true` is set on `guineacam01`. Configure routing rules separately, for example through Traefik dynamic config or extra labels.

## Notes

Each container exposes its MJPEG stream on port `8080` internally (mapped to `1800N` on the host). You can view streams directly in a browser or embed them in Home Assistant with a camera card.
