# Server NFS

This role configures a host as an NFS server. It installs `nfs-kernel-server` and exports ZFS datasets, through the `sharenfs` ZFS property. This ZFS-native NFS sharing, rather than `/etc/exports`, keeps the NFS export configuration together with the dataset definition. It also survives dataset renames or moves, with no separate exports file to keep in sync.

## What it does

The role installs `nfs-common` and `nfs-kernel-server`. It then goes through `zfs_nfs_exports` and sets the `sharenfs` property on each listed dataset. ZFS registers the export with the NFS daemon automatically.

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
| `zfs_nfs_exports` | List of `{ dataset, options }` dicts. If undefined, the role does nothing. |
