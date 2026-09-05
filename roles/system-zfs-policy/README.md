# system-zfs-policy

Policy-driven ZFS snapshot management using systemd timers.

## Overview

This role configures automated ZFS snapshots, based on dataset policy levels. It integrates with the existing `zfs` host variable structure.

## Requirements

- You must define the `zfs` variable in host_vars
- Apply the `system-zfs` role first, to create pools and datasets

## How It Works

### Policy System

Each dataset gets a `policy` level, which determines its snapshot schedule:

| Policy     | Hourly | Daily | Monthly | Yearly | Description            |
| ---------- | ------ | ----- | ------- | ------ | ---------------------- |
| `none`     | 0      | 0     | 0       | 0      | No snapshots (default) |
| `low`      | 3      | 7     | 1       | 0      | Light protection       |
| `high`     | 24     | 14    | 1       | 1      | Standard protection    |
| `critical` | 36     | 30    | 3       | 5      | Maximum protection     |

### Configuration

Set policy on datasets in your `host_vars`:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical    # Gets 36 hourly, 3 monthly, 5 yearly
      scratch:                  # No policy = 'none', no snapshots
      media:
        policy: low         # Gets 3 hourly, 1 monthly
```

### Advanced Features

#### Policy Inheritance (`children_inherit_policy`)

Parent datasets can pass their policy to declared children. This reduces duplication in configuration:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical
        children_inherit_policy: true
        datasets:
          gitea:              # Inherits 'critical'
          jellyfin:           # Inherits 'critical'
          logs:
            policy: none  # Override with explicit value
```

**Use case:** Use this for Docker Compose parent datasets, where most containers share the same backup policy but a few need exceptions.

#### Runtime Child Discovery (`snapshots_discover_children`)

This automatically discovers and snapshots child datasets created outside Ansible (for example, Docker volumes):

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical
        snapshots_discover_children: true  # Snapshots all Docker-created children
```

When `snapshots_discover_children: true`, the snapshot scripts query ZFS at runtime to find all child datasets and apply the parent's policy to them. This is essential for Docker environments where volume datasets are created dynamically.

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
        policy: critical
        children_inherit_policy: true        # For declared children
        snapshots_discover_children: true     # For Docker volumes
        datasets:
          logs:
            policy: none        # Explicitly skip this one
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

Find the scripts in `/opt/zfs-policy/`:

- `zfs-snapshot` - Creates snapshots for datasets based on policy
- `zfs-prune` - Removes old snapshots that exceed the retention limit

### Systemd Units

The role installs services and timers to `/etc/systemd/system/`.

## Manual Usage

Both scripts support manual execution with debug and dry-run modes.

**Note:** Actual snapshot operations need root privileges. You can use `sudo`, or use `--dry-run` to avoid needing them:

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

Find all variables in `defaults/main.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `system_zfs_policy_snapshots_enable` | `true` | Enable/disable automatic snapshots |
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

The snapshot naming convention works with the backup scripts. These scripts need the snapshots to exist for incremental sends.
