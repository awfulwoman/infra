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

| Policy     | Hourly | Daily | Monthly | Yearly | Description            |
| ---------- | ------ | ----- | ------- | ------ | ---------------------- |
| `none`     | 0      | 0     | 0       | 0      | No snapshots (default) |
| `low`      | 3      | 7     | 1       | 0      | Light protection       |
| `high`     | 24     | 14    | 1       | 1      | Standard protection    |
| `critical` | 36     | 30    | 3       | 5      | Maximum protection     |

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

### Advanced Features

#### Policy Inheritance (`children_inherit_policy`)

Parent datasets can pass their importance to declared children, reducing configuration duplication:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
        children_inherit_policy: true
        datasets:
          gitea:              # Inherits 'critical'
          jellyfin:           # Inherits 'critical'
          logs:
            importance: none  # Override with explicit value
```

**Use case:** Docker Compose parent datasets where most containers share the same backup policy, with occasional exceptions.

#### Runtime Child Discovery (`snapshots_discover_children`)

Automatically discover and snapshot child datasets created outside of Ansible (e.g., Docker volumes):

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
        snapshots_discover_children: true  # Snapshots all Docker-created children
```

When `snapshots_discover_children: true`, the snapshot scripts query ZFS at runtime to find all child datasets and apply the parent's importance policy to them. This is essential for Docker environments where volume datasets are created dynamically.

**Observing discoveries:**
```bash
sudo /opt/zfs-policy/zfs-snapshot --type hourly --dry-run --debug
```

#### Combining Both Features

You can use both together to handle declared children (with inheritance) and undeclared children (with discovery):

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
        children_inherit_policy: true        # For declared children
        snapshots_discover_children: true     # For Docker volumes
        datasets:
          logs:
            importance: none        # Explicitly skip this one
```

**For detailed documentation**, including use cases, troubleshooting, and feature comparisons, see [docs/zfs.md](../../docs/zfs.md#advanced-dataset-policy-management).

### Snapshot Naming

Snapshots follow a consistent naming convention:

```
autosnap_YYYY-MM-DD_HH:MM:SS_hourly
autosnap_YYYY-MM-DD_HH:MM:SS_daily
autosnap_YYYY-MM-DD_HH:MM:SS_monthly
autosnap_YYYY-MM-DD_HH:MM:SS_yearly
```

### Schedule

| Timer                        | Schedule              | Description               |
| ---------------------------- | --------------------- | ------------------------- |
| `zfs-snapshot-hourly.timer`  | Every hour at :00     | Creates hourly snapshots  |
| `zfs-snapshot-daily.timer`   | Daily at 00:15        | Creates daily snapshots   |
| `zfs-snapshot-monthly.timer` | 1st of month at 00:20 | Creates monthly snapshots |
| `zfs-snapshot-yearly.timer`  | Jan 1st at 00:25      | Creates yearly snapshots  |
| `zfs-prune.timer`            | Every hour at :30     | Removes expired snapshots |

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
