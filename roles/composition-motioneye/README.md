# MotionEye

[MotionEye](https://github.com/motioneye-project/motioneye) is a web-based frontend for the `motion` daemon, providing a UI to manage IP cameras and USB cameras with motion detection, recording, and live streaming.

The container runs as `privileged: true` to support USB camera access. An optional USB device path and ZFS pool drive ID can be configured per-host. If `composition_motioneye_zfsdriveid` is set, the role will create a ZFS pool named `fastpool` for storage.

The subdomain is host-scoped: `motioneye.<hostname>.<domain>` — this allows multiple MotionEye instances on different hosts.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_motioneye_usbdevice` | `false` | USB device path to pass through (e.g. `/dev/video0`) |
| `composition_motioneye_zfsdriveid` | `false` | ZFS drive ID to create a `fastpool` storage pool |

## Ports

| Port | Purpose |
|------|---------|
| `8081` | MotionEye web UI |
| `9081` | Motion stream port |
| `8765` | Traefik-routed port |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/shared` | Shared recordings/captures |
| `{{ composition_config }}/etc` | MotionEye configuration |
