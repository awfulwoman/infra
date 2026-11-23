# Jellyfin

[Jellyfin](https://jellyfin.org) is a free and open-source media server for streaming films, TV shows, music, and photos. It provides a web interface, mobile apps, and smart TV clients, and handles transcoding, metadata fetching, and user management.

The role serves media from the shared media path (`{{ shared_media_path }}`). Set this path per host — typically an NFS or ZFS share.

## Ports

`8096:8096` (also exposed via Traefik at `jellyfin.<domain>` and `jellyfin-vue.<domain>`).

## Key variables

| Variable | Description |
|----------|-------------|
| `shared_media_path` | Path to the media library (set in host/group vars) |
| `composition_jellyfin_render_gid` | Derived, not set by hand: the host's `render` group GID, defined only when a render device exists |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/config` | Jellyfin configuration and database |
| `{{ composition_config }}/cache` | Transcoding cache and image cache |
| `{{ shared_media_path }}` | Media library (mounted at `/data`) |

## Hardware transcoding

Jellyfin transcodes on the host's Intel QuickSync iGPU. The role maps `/dev/dri` into the container and adds the host's `render` group GID, because `renderD128` is `root:render 0660` and the container is not guaranteed to run as root.

The GID is read from the host at run time (`getent group render`), so nothing is hardcoded. A host with no `/dev/dri/renderD128` gets neither key — Docker refuses to create a container that names a device the host does not have.

The image ships Jellyfin's own ffmpeg build, which includes `vainfo` — the system `vainfo` package is not in the image. Verify after deploying:

```bash
docker exec jellyfin /usr/lib/jellyfin-ffmpeg/vainfo
```

A working setup lists the `iHD` driver and the codecs the iGPU supports. Then enable it in Jellyfin: **Dashboard → Playback → Intel QuickSync (QSV)**, leaving the device at `/dev/dri/renderD128`.

## DNS

Registers subdomains: `jellyfin`, `jellyfin-vue`
