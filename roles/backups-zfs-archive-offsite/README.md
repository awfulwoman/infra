# ZFS archive - off-site

A ZFS archive is the final step in this backup solution.

1. Each ZFS-enabled machine stores its own snapshots.
2. The central backup server pulls the snapshots into an encrypted dataset.
3. The backup server pushes snapshots to a local archive and to a remote off-site archive. The remote archive is untrusted. It receives only raw encrypted backups, with no key loading.

A ZFS archive can only receive backups. It cannot pull backups from other hosts.

## Prerequisites

You must create the destination dataset before you run this role. Define it in the host's `zfs:` variable configuration with encryption enabled:

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

These settings let the dataset receive raw encrypted sends from the backup server. The role fails with an assertion error if the dataset does not exist.
