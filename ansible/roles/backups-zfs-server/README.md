# ZFS Backups

This role sets this host as a backup server. It allows ZFS datasets to be _pushed_ and/or _pulled_ to and from hosts configured with `backups-zfs-client`. The newly configured backup host thus acts as the controller for ZFS backups, enabling the pulling of datasets from other hosts to its own encrypted datasets, and pushing those encrypted off-site to potentially less trusted hosts.

## Push vs Pull

Note the _pulling_ and _pushing_ of datasets. The other hosts are deliberately never given the ability to directly connect to the backup host. Instead the backup host performs an SSH connection to each machine and either initiates a `zfs send` from that machine to itself using a locked-down user, or starts `zfs receive` and pushes directly to an off-site host.

## Policy-driven backups

In a host's `zfs` config each and every dataset can have the `importance` attribute marked. This is utilised by both the `backup-zfs-*` roles and the `system-zfs-policy` role.

## Commands

### zfs-pull-backups

Pulls ZFS datasets from a remote host to the local backup server. Automatically handles initial full syncs and subsequent incremental transfers.

```bash
zfs-pull-backups --host <hostname> --datasets <dataset1> [dataset2 ...] [options]
```

**Required arguments:**

- `--host` - Remote host to pull from
- `--datasets` - Space-separated list of source datasets on the remote host

**Optional arguments:**

- `--user` - SSH user for remote connection (default: configured vault user)
- `--destination` - Local dataset to receive backups (default: configured backup dataset)
- `--debug` - Enable debug output showing commands and detailed progress
- `--quiet`, `-q` - Suppress informational output (errors still shown)

**Example:**
```bash
zfs-pull-backups --host server1 --datasets tank/data tank/media --debug
```

### zfs-push-backups

Pushes ZFS datasets from the local backup server to a remote host (typically off-site storage). Uses raw send (`-w`) to preserve encryption. Automatically handles initial full syncs and subsequent incremental transfers.

```bash
zfs-push-backups --host <hostname> --datasets <dataset1> [dataset2 ...] --destination <remote-dataset> [options]
```

**Required arguments:**

- `--host` - Remote host to push to
- `--datasets` - Space-separated list of local source datasets to push
- `--destination` - Remote dataset to receive backups

**Optional arguments:**

- `--user` - SSH user for remote connection (default: configured vault user)
- `--strip-prefix` - Prefix to strip from dataset paths (default: configured backup dataset)
- `--debug` - Enable debug output showing commands and detailed progress
- `--quiet`, `-q` - Suppress informational output (errors still shown)

**Example:**

```bash
zfs-push-backups --host offsite-server --datasets backuppool/encryptedbackups/server1/tank/data --destination offsite/backups
```
