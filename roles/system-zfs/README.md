# System ZFS

Installs ZFS utilities on Ubuntu, imports or creates zpools, configures native encryption, and ensures datasets exist with the declared properties.

A `zfs` host variable (defined in `host_vars`) drives the role. This variable describes the wanted pool and dataset structure. A custom Ansible filter plugin (`zfs_datasets.py`) processes this declarative structure into the flat lists the role iterates over.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `zfs` | _(required)_ | Declarative ZFS structure defined in `host_vars`. Must include pool names, optional `vdevs`, and dataset definitions with optional `properties`. |
| `zfs_pools_create` | `false` | Allow the role to create pools that do not exist. Disabled by default as a safety measure: pools must exist before the role provisions datasets. |
| `vault_zfs_passphrase` | _(required if encryption used)_ | Passphrase for encrypted datasets, stored in Ansible Vault. The role writes it to `/root/zfs/passphrase`. A systemd service loads it at boot. |

## Encryption

When any dataset in the `zfs` structure declares an `encryption` property, the role:

1. Writes the passphrase to `/root/zfs/passphrase` (root-readable only).
2. Deploys a `zfs-load-key.service` systemd unit that runs `zfs load-key -a` after `zfs-import.target` and before `zfs-mount.service`.

This unlocks encrypted pools automatically at boot without interactive input.

## Design Notes

- The role applies ZFS properties only when it creates a dataset, not on later runs. It has no way to detect which properties are mutable and which are static. As a result, the role does not correct drift in dataset properties. A comment in the task file notes this limitation.
- The role tries to import inactive pools before it creates them. This handles the case of a pool that exists on a block device but is not yet imported into the running system.
- Pool creation (`zfs_pools_create: true`) requires you to declare `vdevs` in the `zfs` variable for that pool.
