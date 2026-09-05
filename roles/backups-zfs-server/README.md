# ZFS Backups

This role sets this host as a backup server. It lets ZFS datasets be _pushed_ and _pulled_ to and from hosts configured with `backups-zfs-client`. The backup host acts as the controller for ZFS backups. It pulls datasets from other hosts into its own encrypted datasets, and pushes those encrypted datasets off-site to less trusted hosts.

## Push vs Pull

The backup host pulls datasets from other hosts, and pushes datasets to off-site hosts. The other hosts never connect directly to the backup host. Instead, the backup host makes an SSH connection to each machine. It then either starts a `zfs send` from that machine to itself with a locked-down user, or starts `zfs receive` and pushes directly to an off-site host.

## Policy-driven backups

In a host's `zfs` config, each dataset can have the `importance` attribute set. Both the `backup-zfs-*` roles and the `system-zfs-policy` role use this attribute.

## Commands

### zfs-pull-backups

Pulls ZFS datasets from a remote host to the local backup server. It handles the first full sync and later incremental transfers on its own.

```bash
zfs-pull-backups --host <hostname> --datasets <dataset1> [dataset2 ...] [options]
```

**Required arguments:**

- `--host` - Remote host to pull from
- `--datasets` - Space-separated list of source datasets on the remote host

**Optional arguments:**

- `--user` - SSH user for the remote connection (default: configured vault user)
- `--destination` - Local dataset that receives backups (default: configured backup dataset)
- `--debug` - Show commands and detailed progress
- `--quiet`, `-q` - Hide informational output (errors still show)

**Example:**
```bash
zfs-pull-backups --host server1 --datasets tank/data tank/media --debug
```

### zfs-push-backups

Pushes ZFS datasets from the local backup server to a remote host, typically off-site storage. It uses raw send (`-w`) to keep encryption intact, and handles the first full sync and later incremental transfers on its own.

```bash
zfs-push-backups --host <hostname> --datasets <dataset1> [dataset2 ...] --destination <remote-dataset> [options]
```

**Required arguments:**

- `--host` - Remote host to push to
- `--datasets` - Space-separated list of local source datasets to push
- `--destination` - Remote dataset that receives backups

**Optional arguments:**

- `--user` - SSH user for the remote connection (default: configured vault user)
- `--strip-prefix` - Prefix to remove from dataset paths (default: configured backup dataset)
- `--debug` - Show commands and detailed progress
- `--quiet`, `-q` - Hide informational output (errors still show)

**Example:**

```bash
zfs-push-backups --host offsite-server --datasets slowpool/encryptedbackups/server1/tank/data --destination offsite/backups
```
