# ZFS Architecture

ZFS is the filesystem of choice for storing important, non-operating system data. All ZFS storage is configured via Ansible roles.

## Definitions

The ZFS configuration for each stored in a `zfs` dictionary item. It defines pools and datasets.

Here is an example:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
  slowpool:
    datasets:
      shared:
        datasets:
          syncthing:
    encrypteddataset:
      importance: critical
      properties:
        encryption: aes-256-gcm
        keylocation: "{{ vault_zfs_default_encryption_passphrase_path }}"
        keyformat: passphrase
```

The top level items underneath the `zfs` item are always pool names.

Below each pool datasets are defined with the `dataset` item.

## Snapshots

ZFS in this infrastructure is policy-driven. This means that policies are defined and then applied to datasets. Policies are assigned to datasets using the `importance` item.

The `system-zfs` Ansible role reads the contents of a hosts `zfs` dictionary and creates pools and datasets.

Another, as yet undefined role (likely to be called `system-zfs-snapshots`), sets up ZFS snapshots via the policy system.

## Replication

The following roles form the core of the ZFS backup and replication system.

- `backups-zfs-client`
- `backups-zfs-server`
- `backups-zfs-archive-offsite`
