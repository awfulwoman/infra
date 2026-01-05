# system-zfs-policy

Policy-driven ZFS snapshot management using systemd timers.

## Overview

This role configures automated ZFS snapshots based on dataset importance levels, integrating with the existing `zfs` host variable structure.

## Requirements

- The `zfs` variable must be defined in host_vars
- The `system-zfs` role should be applied first to create pools and datasets

## How It Works

### Policy System

Datasets are assigned an `importance` level which determines their snapshot schedule:

| Policy     | Hourly | Monthly | Yearly | Description            |
| ---------- | ------ | ------- | ------ | ---------------------- |
| `none`     | 0      | 0       | 0      | No snapshots (default) |
| `low`      | 3      | 1       | 0      | Light protection       |
| `high`     | 24     | 1       | 1      | Standard protection    |
| `critical` | 36     | 3       | 5      | Maximum protection     |

### Configuration

Set importance on datasets in your `host_vars`:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical    # Gets 36 hourly, 3 monthly, 5 yearly
      scratch:                  # No importance = 'none', no snapshots
      media:
        importance: low         # Gets 3 hourly, 1 monthly
```

### Snapshot Naming

Snapshots follow a consistent naming convention:

```
autosnap_YYYY-MM-DD_HH:MM:SS_hourly
autosnap_YYYY-MM-DD_HH:MM:SS_monthly
autosnap_YYYY-MM-DD_HH:MM:SS_yearly
```

### Schedule

| Timer | Schedule | Description |
|-------|----------|-------------|
| `zfs-snapshot-hourly.timer` | Every hour at :00 | Creates hourly snapshots |
| `zfs-snapshot-monthly.timer` | 1st of month at 00:05 | Creates monthly snapshots |
| `zfs-snapshot-yearly.timer` | Jan 1st at 00:10 | Creates yearly snapshots |
| `zfs-prune.timer` | Every hour at :30 | Removes expired snapshots |

## Installed Components

### Scripts

Located in `/opt/zfs-policy/`:

- `zfs-snapshot` - Creates snapshots for datasets based on policy
- `zfs-prune` - Removes old snapshots exceeding retention limits

### Systemd Units

Services and timers are installed to `/etc/systemd/system/`.

## Manual Usage

Both scripts support manual execution with debug and dry-run modes.

**Note:** Root privileges are required for actual snapshot operations. Use `sudo` or `--dry-run`:

```bash
# Preview what snapshots would be created (no sudo needed)
/opt/zfs-policy/zfs-snapshot --type hourly --dry-run --debug

# Preview what would be pruned (no sudo needed)
/opt/zfs-policy/zfs-prune --dry-run --debug

# Actually create snapshots (requires sudo)
sudo /opt/zfs-policy/zfs-snapshot --type hourly

# Check timer status
systemctl list-timers 'zfs-*'

# View recent activity
journalctl -u zfs-snapshot-hourly --since "1 hour ago"
```

## Role Variables

All variables are defined in `defaults/main.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `system_zfs_policy_snapshot_prefix` | `autosnap` | Prefix for snapshot names |
| `system_zfs_policy_script_path` | `/opt/zfs-policy` | Script installation path |
| `system_zfs_policy_log_dir` | `/var/log/zfs-policy` | Log directory |
| `system_zfs_policy_definitions` | (see defaults) | Policy retention counts |
| `system_zfs_policy_timer_hourly` | `*:00` | Hourly timer schedule |
| `system_zfs_policy_timer_monthly` | `*-*-01 00:05` | Monthly timer schedule |
| `system_zfs_policy_timer_yearly` | `*-01-01 00:10` | Yearly timer schedule |
| `system_zfs_policy_timer_prune` | `*:30` | Prune timer schedule |

## Integration with Backups

This role handles local snapshots only. The `backups-zfs-client` and `backups-zfs-server` roles handle replication of snapshots to the backup infrastructure.

The snapshot naming convention is compatible with the backup scripts, which rely on snapshots being present for incremental sends.
