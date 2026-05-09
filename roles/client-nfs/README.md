# Client NFS

Mounts remote NFS shares on a host. Supports both Ubuntu/Debian (via `nfs-common` and `/etc/fstab`) and macOS. Mount failures are non-fatal — the role logs a debug message and continues, which prevents a temporarily unreachable NFS server from blocking the rest of a playbook run.

## Platform Behaviour

- **Ubuntu/Debian:** Installs `nfs-common`, then mounts each share with `ansible.posix.mount` using systemd-aware options (`_netdev`, `x-systemd.after=network-online.target`) so mounts are deferred until the network is available.
- **macOS:** Mounts shares using macOS-compatible NFS options (`resvport,rw`). No package installation needed.

## Variables

Define `nfs_mounts` in `host_vars` as a list of mount definitions:

```yaml
nfs_mounts:
  - remote_server: host-generic-64gb-storage
    remote_path: /slowpool/shared/media
    local_path: /mnt/media
  - remote_server: host-generic-8gb-backups
    remote_path: /fastpool/archive
    local_path: /mnt/archive
    nfsclient_mount_options: "defaults,_netdev,ro"  # optional per-mount override
```

| Variable | Default | Description |
|---|---|---|
| `nfs_mounts` | *(undefined)* | List of NFS mounts; role is a no-op if not defined |
| `nfsclient_mount_options` | `defaults,_netdev,x-systemd.after=network-online.target` | Default mount options for Linux |
| `nfsclient_mount_options_macos` | `resvport,rw` | Default mount options for macOS |

Per-mount `nfsclient_mount_options` overrides the role default for that entry only.
