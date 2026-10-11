# Offsite copy with restic

This role makes the backup server send its `critical` replicas to a Hetzner Storage Box with restic. It is the Offsite copy. See [ADR-0002](../../docs/adr/0002-offsite-copy-is-a-restic-repository.md) for the reasons.

The role is separate from the ZFS push path (`backups-zfs-archive-offsite`). It does not replace that path.

## How it works

1. The role builds the target list from every `critical` dataset of every host in `zfs_backup_clients`. This is the same `zfs_offsite_datasets` filter that the ZFS push uses.
2. Once a day, `zfs-offsite-restic backup` runs from cron. For each target it finds the newest snapshot of the replica, puts a ZFS hold on it, mounts it read-only below `/run/offsite-restic`, and runs `restic backup`.
3. The smallest targets go first. The first run takes more than a week, and the small datasets are the ones that cannot be replaced.
4. A target whose newest snapshot is already in the repository is skipped. A run that stops half-way therefore continues where it stopped.
5. `restic forget` applies the retention. `restic prune` runs weekly, and `restic check` reads back a sample monthly.
6. The job publishes its status to MQTT after each target. Home Assistant shows one binary sensor, `<host> Offsite Backups`, with the missing, stale and failed targets as attributes.

A second run does not start while one is in progress.

## Setup

Do these steps in order.

1. Add the secrets to Ansible Vault. Storage Box passwords need upper case, lower case, a digit and a special character, so a suffix is added to the generated value.

   ```bash
   ansible-vault encrypt_string "$(openssl rand -hex 32)Aa1!" --name 'vault_offsite_storagebox_password'
   ansible-vault encrypt_string "$(openssl rand -hex 32)Aa1!" --name 'vault_offsite_storagebox_subaccount_password'
   ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_offsite_restic_repo_password'
   ```

2. Copy `vault_offsite_restic_repo_password` to a place that does not depend on this infrastructure. Without it the Offsite copy cannot be read.
3. Run the playbook that has `infra-public-resources`. Terraform creates the Storage Box and its `restic` sub-account, and the play prints the sub-account's host and user.
4. Put those two values in the backup server's `host_vars`, and set `backups_restic_offsite_enabled: true`.
5. Run the backup server's playbook. The role installs an SSH key on the sub-account, initialises the repository, and installs the cron jobs.

## Commands

Run these on the backup server, as root. The wrapper loads the repository settings.

```bash
# Any restic command
/opt/zfsbackup/scripts/offsite-restic.sh restic snapshots
/opt/zfsbackup/scripts/offsite-restic.sh restic stats

# Start a run by hand
/opt/zfsbackup/scripts/offsite-restic.sh backup

# Follow a run
journalctl -t offsite-restic -f
```

## Restore

Each target is stored with the client as the restic host, and with the path `/run/offsite-restic/<client>/<dataset>`.

```bash
/opt/zfsbackup/scripts/offsite-restic.sh restic restore latest \
  --host server-64gb-storage \
  --path /run/offsite-restic/server-64gb-storage/slowpool/charlie/financial \
  --target /tmp/restore
```

To restore without the backup server, you need restic, the repository password, and SFTP access to the Storage Box. The main Storage Box account can read the repository at `restic/restic`.

If the repository itself is damaged or deleted, restore a Storage Box snapshot from the Hetzner console first.

## Limits

- A restore gives files, not a ZFS dataset. Snapshot history and dataset properties are not in the Offsite copy.
- Databases are crash-consistent, as they are in the replicas.
- A `critical` dataset on a host that is not in `zfs_backup_clients` has no replica, so it is reported as failed.
