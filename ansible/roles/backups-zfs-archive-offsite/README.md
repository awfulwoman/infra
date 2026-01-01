# ZFS archive - off-site

A ZFS archive is the final step in my backup solution.

1. Snapshots are stored on each ZFS-enabled machine
2. Snapshots are pulled to a central backup server, underneath an encrypted dataset.
3. From the backup server snapshots are pushed to a local archive and to a remote off-site archive. The remote archive is untrusted and only receives raw encrypted backups with no key loading.

ZFS archives can only passively receive backups - they have no capacity for active pulling backups from elsewhere.
