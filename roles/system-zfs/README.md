# System ZFS

Installs ZFS utilities on Ubuntu, imports or creates zpools, configures native encryption, and ensures datasets exist with the declared properties.

The role is driven by a `zfs` host variable (defined in `host_vars`) that describes the desired pool and dataset structure. A custom Ansible filter plugin (`zfs_datasets.py`) processes this declarative structure into the flat lists the role iterates over.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `zfs` | _(required)_ | Declarative ZFS structure defined in `host_vars`. Must include pool names, optional `vdevs`, and dataset definitions with optional `properties`. |
| `zfs_pools_create` | `false` | Allow the role to create pools that don't exist. Disabled by default as a safety measure — pools should exist before datasets are provisioned. |
| `vault_zfs_passphrase` | _(required if encryption used)_ | Passphrase for encrypted datasets. Stored in Ansible Vault. Written to `/root/zfs/passphrase` and loaded at boot via a systemd service. |

## Encryption

When any dataset in the `zfs` structure declares an `encryption` property, the role:

1. Writes the passphrase to `/root/zfs/passphrase` (root-readable only).
2. Deploys a `zfs-load-key.service` systemd unit that runs `zfs load-key -a` after `zfs-import.target` and before `zfs-mount.service`.

This means encrypted pools are unlocked automatically at boot without interactive input.

## Design Notes

- ZFS properties are only applied on dataset creation, not on subsequent runs. There is no mechanism to detect which properties are mutable vs. static, so drift in dataset properties will not be corrected idempotently. A comment in the task file acknowledges this limitation.
- The role attempts to import inactive pools before creating them, handling the case where a pool exists on a block device but hasn't been imported into the running system.
- Pool creation (`zfs_pools_create: true`) requires `vdevs` to be declared in the `zfs` variable for that pool.
