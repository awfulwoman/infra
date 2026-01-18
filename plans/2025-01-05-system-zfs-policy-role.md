# Implementation Plan: `system-zfs-policy` Ansible Role

## Overview

Create a new Ansible role for policy-driven ZFS snapshots, replacing Sanoid. Uses systemd timers for scheduling and Python scripts for operations.

## Policy Definitions (from docs/zfs.md)

| Policy    | Hourly | Monthly | Yearly | Autosnap | Autoprune |
| --------- | ------ | ------- | ------ | -------- | --------- |
| `none`    | 0      | 0       | 0      | FALSE    | FALSE     |
| `low`     | 3      | 1       | 0      | TRUE     | TRUE      |
| `high`    | 24     | 1       | 1      | TRUE     | TRUE      |
| `critical`| 36     | 3       | 5      | TRUE     | TRUE      |

## Role Structure

```
ansible/roles/system-zfs-policy/
├── defaults/main.yaml          # Policy definitions, paths, timer schedules
├── handlers/main.yaml          # systemd daemon-reload handler
├── tasks/main.yaml             # Deployment logic
└── templates/
    ├── zfs-snapshot.py.j2      # Snapshot creation script
    ├── zfs-prune.py.j2         # Snapshot pruning script
    ├── zfs-snapshot-hourly.service.j2
    ├── zfs-snapshot-hourly.timer.j2
    ├── zfs-snapshot-monthly.service.j2
    ├── zfs-snapshot-monthly.timer.j2
    ├── zfs-snapshot-yearly.service.j2
    ├── zfs-snapshot-yearly.timer.j2
    ├── zfs-prune.service.j2
    └── zfs-prune.timer.j2
```

## Implementation Steps

### Step 1: Add New Filter Plugin

**File:** `ansible/plugins/filters/zfs_datasets.py`

Add `zfs_datasets_with_importance` filter to extract datasets with their importance level:
- Returns list of `{dataset: "pool/path", importance: "critical|high|low|none"}`
- Defaults to `none` if no importance specified
- Recursively walks nested datasets

### Step 2: Create Role Defaults

**File:** `ansible/roles/system-zfs-policy/defaults/main.yaml`

```yaml
system_zfs_policy_snapshot_prefix: "autosnap"
system_zfs_policy_script_path: /opt/zfs-policy
system_zfs_policy_log_dir: /var/log/zfs-policy

# Policy definitions (retention counts)
system_zfs_policy_definitions:
  none:   {hourly: 0,  monthly: 0, yearly: 0, autosnap: false, autoprune: false}
  low:    {hourly: 3,  monthly: 1, yearly: 0, autosnap: true,  autoprune: true}
  high:   {hourly: 24, monthly: 1, yearly: 1, autosnap: true,  autoprune: true}
  critical: {hourly: 36, monthly: 3, yearly: 5, autosnap: true,  autoprune: true}

# Timer schedules (systemd OnCalendar format)
system_zfs_policy_timer_hourly: "*:00"
system_zfs_policy_timer_monthly: "*-*-01 00:05"
system_zfs_policy_timer_yearly: "*-01-01 00:10"
system_zfs_policy_timer_prune: "*:30"
```

### Step 3: Create Python Scripts

**Snapshot Script** (`templates/zfs-snapshot.py.j2`):
- Arguments: `--type hourly|monthly|yearly`, `--debug`, `--dry-run`
- Iterates datasets, checks if policy requires this snapshot type
- Creates snapshots named: `autosnap_YYYY-MM-DD_HH:MM:SS_{type}`
- Follows patterns from existing `zfs-pull-backups.py`

**Prune Script** (`templates/zfs-prune.py.j2`):
- Arguments: `--debug`, `--dry-run`
- Lists existing snapshots matching our naming convention
- Groups by type (hourly/monthly/yearly)
- Keeps N most recent per policy, destroys excess

### Step 4: Create Systemd Units

**Timers:**
- `zfs-snapshot-hourly.timer` - runs every hour on the hour
- `zfs-snapshot-monthly.timer` - runs 1st of month at 00:05
- `zfs-snapshot-yearly.timer` - runs Jan 1st at 00:10
- `zfs-prune.timer` - runs every hour at :30 (after snapshots)

**Services:** Each timer has matching `.service` unit that runs the script.

### Step 5: Create Ansible Tasks

**File:** `ansible/roles/system-zfs-policy/tasks/main.yaml`

1. Assert `zfs` variable is defined
2. Create script directory `/opt/zfs-policy`
3. Create log directory `/var/log/zfs-policy`
4. Deploy Python scripts (zfs-snapshot, zfs-prune)
5. Deploy systemd service and timer units
6. Flush handlers (reload systemd)
7. Enable and start all timers

### Step 6: Remove Sanoid from `backups-zfs-client`

**File:** `ansible/roles/backups-zfs-client/tasks/main.yaml`

Remove these tasks:
- Sanoid package installation (keep acl, moreutils, lzop, mbuffer)
- `/etc/sanoid` directory creation
- Sanoid config file creation
- Sanoid timer enablement

**Keep** these tasks (still needed for backup replication):
- Backup user creation (UID 1099)
- SSH key deployment
- ZFS delegation permissions

### Step 7: Test and Validate

1. Run role on a test host with `--check` mode first
2. Use `--dry-run` flags on scripts to verify dataset discovery
3. Monitor systemd timers with `systemctl list-timers`
4. Check journal logs with `journalctl -u zfs-snapshot-hourly`

## Files to Modify/Create

| File | Action |
|------|--------|
| `ansible/plugins/filters/zfs_datasets.py` | Add `zfs_datasets_with_importance` filter |
| `ansible/roles/system-zfs-policy/` | Create entire role (new) |
| `ansible/roles/backups-zfs-client/tasks/main.yaml` | Remove Sanoid-related tasks |

## Snapshot Naming Convention

```
autosnap_YYYY-MM-DD_HH:MM:SS_hourly
autosnap_YYYY-MM-DD_HH:MM:SS_monthly
autosnap_YYYY-MM-DD_HH:MM:SS_yearly
```

Compatible with existing backup scripts that rely on snapshot presence.

## Testing

Both scripts support safe testing:
```bash
/opt/zfs-policy/zfs-snapshot --type hourly --dry-run --debug
/opt/zfs-policy/zfs-prune --dry-run --debug
```

## Design Decisions

- **No inheritance**: Importance is NOT inherited from parent datasets (explicit per-dataset)
- **Scripts on each host**: Policy definitions baked into scripts via Jinja2 templating
- **Error handling**: Individual failures logged but don't stop processing; exit 1 if any failures
- **Persistent timers**: Systemd `Persistent=true` catches up if host was down
