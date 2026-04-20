# Server NFS

Configures a host as an NFS server by installing `nfs-kernel-server` and exporting ZFS datasets via the `sharenfs` ZFS property. Using ZFS-native NFS sharing rather than `/etc/exports` means NFS export configuration is co-located with the dataset definition and survives dataset renames or moves without needing a separate exports file to stay in sync.

## What it does

Installs `nfs-common` and `nfs-kernel-server`, then iterates `zfs_nfs_exports` and sets the `sharenfs` property on each listed dataset. ZFS handles registering the export with the NFS daemon automatically.

## Variables

Define `zfs_nfs_exports` in `host_vars` as a list of dataset and options pairs:

```yaml
zfs_nfs_exports:
  - dataset: slowpool/shared/media
    options: "rw=@192.168.1.0/24,no_subtree_check"
  - dataset: fastpool/archive
    options: "ro=@192.168.1.0/24,no_subtree_check"
```

| Variable | Description |
|---|---|
| `zfs_nfs_exports` | List of `{ dataset, options }` dicts. Role is a no-op if not defined. |
