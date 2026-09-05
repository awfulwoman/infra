# Client NFS

This role mounts remote NFS shares on a host. It supports Ubuntu/Debian, through `nfs-common` and `/etc/fstab`, and macOS. A mount failure does not stop the role. The role logs a debug message and continues, so a temporarily unreachable NFS server does not block the rest of a playbook run.

## Platform Behavior

- **Ubuntu/Debian:** Installs `nfs-common`, then mounts each share with `ansible.posix.mount`, using systemd-aware options (`_netdev`, `x-systemd.after=network-online.target`). This delays mounts until the network is available.
- **macOS:** Mounts shares with macOS-compatible NFS options (`resvport,rw`). This needs no package installation.

## Variables

Define `nfs_mounts` in `host_vars` as a list of mount definitions:

```yaml
nfs_mounts:
  - remote_server: server-64gb-storage
    remote_path: /slowpool/shared/media
    local_path: /mnt/media
  - remote_server: server-8gb-backups
    remote_path: /fastpool/archive
    local_path: /mnt/archive
    nfsclient_mount_options: "defaults,_netdev,ro"  # optional per-mount override
```

| Variable | Default | Description |
|---|---|---|
| `nfs_mounts` | *(undefined)* | List of NFS mounts. The role does nothing if this is not defined. |
| `nfsclient_mount_options` | `defaults,_netdev,x-systemd.after=network-online.target` | Default mount options for Linux |
| `nfsclient_mount_options_macos` | `resvport,rw` | Default mount options for macOS |

A per-mount `nfsclient_mount_options` value overrides the role default, for that entry only.
