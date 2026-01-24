# ZFS archive - off-site

A ZFS archive is the final step in my backup solution.

1. Snapshots are stored on each ZFS-enabled machine
2. Snapshots are pulled to a central backup server, underneath an encrypted dataset.
3. From the backup server snapshots are pushed to a local archive and to a remote off-site archive. The remote archive is untrusted and only receives raw encrypted backups with no key loading.

ZFS archives can only passively receive backups - they have no capacity for active pulling backups from elsewhere.

## Prerequisites

The destination dataset must be created **before** running this role. Define it in the host's `zfs:` variable configuration with encryption enabled:

```yaml
zfs:
  poolname:
    datasets:
      encryptedbackups:
        properties:
          encryption: aes-256-gcm
          keylocation: "{{ vault_zfs_default_encryption_passphrase_path }}"
          keyformat: passphrase
```

This ensures the dataset has proper encryption settings to receive raw encrypted sends from the backup server. The role will fail with an assertion error if the dataset does not exist.
