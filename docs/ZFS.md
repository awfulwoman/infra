# ZFS Architecture

ZFS is the file system for important, non-operating-system data. Ansible roles configure all ZFS storage.

## Defining ZFS configuration

Each host stores its ZFS configuration in a `zfs` dictionary item. This item defines both pools and datasets.

Example:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical
  slowpool:
    datasets:
      shared:
        datasets:
          syncthing:
    encrypteddataset:
      policy: critical
      properties:
        encryption: aes-256-gcm
        keylocation: "{{ vault_zfs_default_encryption_passphrase_path }}"
        keyformat: passphrase
```

The items directly below the `zfs` key are always pool names.

Define a pool's datasets below the pool, with the `datasets` key.

A dataset can have child datasets. Child datasets also use the `datasets` key.

## Policy-driven snapshots and replication

This infrastructure uses policies to drive ZFS snapshots and replication. You define a policy, then apply it to a dataset. The `policy` key assigns a policy to a dataset.

Relevant roles:

- `system-zfs`: configures ZFS on a host by reading the `zfs` dictionary variable and creating the defined pools and datasets.
- `system-zfs-policy`: configures a host's ZFS snapshots through the policy system.
- `backups-zfs-server`: configures a host that replicates snapshots to itself via a pull mechanism. At least one host with this role is critical for backup operations.
- `backups-zfs-client`: configures a host so that a `backups-zfs-server` host can pull its dataset snapshots.
- `backups-zfs-offsite`: configures a host so that a `backups-zfs-server` host can push dataset snapshots to it.

## Advanced Dataset Policy Management

ZFS policy management has two features for dataset policy at scale: **policy inheritance** and **runtime child discovery**. These features solve different, but related, problems.

### Policy Inheritance with `children_inherit_policy`

Policy inheritance is a **configuration-time** feature. A parent dataset can automatically pass its policy value to child datasets that you declare in Ansible inventory.

#### How It Works

When a dataset has `children_inherit_policy: true`, all its child datasets automatically inherit the parent's policy level **unless** they explicitly define their own policy. This inheritance happens during Ansible's configuration processing, before any scripts run.

#### Use Case: Mixed-Priority Docker Compose Applications

A common case is a parent dataset that contains multiple Docker Compose applications. Most of them use the parent's backup level, but a few need different treatment.

**Example from `dns` host:**

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical
        children_inherit_policy: true
        datasets:
          awfulwoman:
            policy: none        # Explicitly override to skip backups
          container-management:
            policy: none        # Explicitly override to skip backups
          reverseproxy:
            policy: none        # Explicitly override to skip backups
          # Other compositions inherit 'critical' automatically
```

**What Happens:**

- `fastpool/compositions` is marked `critical` with `children_inherit_policy: true`
- `fastpool/compositions/awfulwoman` explicitly sets `policy: none` → gets `none` (override)
- `fastpool/compositions/container-management` explicitly sets `policy: none` → gets `none` (override)
- `fastpool/compositions/reverseproxy` explicitly sets `policy: none` → gets `none` (override)
- Any other composition dataset inherits `critical` from its parent

This pattern is simpler than setting `policy: critical` on every composition dataset.

#### When to Use `children_inherit_policy`

- **Docker Compose parent datasets** where most containers use the same backup level
- **Media libraries** with consistent policy (for example, all music folders are critical, all TV shows are low)
- **Shared datasets** where you want a default policy but occasional overrides
- **Development environments** with a baseline policy and specific exceptions

### Runtime Child Discovery with `snapshots_discover_children`

Runtime child discovery is a **runtime** feature. It automatically finds and applies policy to child datasets that Docker creates, but that are not declared in Ansible inventory.

#### How It Works

When a dataset has `snapshots_discover_children: true`, the snapshot and pruning scripts query ZFS at runtime to find all child datasets that actually exist on the system. Discovered children automatically receive the same policy as their parent.

This happens every time the scripts run. As a result, the next snapshot cycle immediately includes newly created children.

#### Use Case: Docker Volume Discovery

Docker automatically creates ZFS datasets for volumes when it uses the ZFS storage driver. These datasets are not in your inventory, because Docker creates them dynamically, based on the `docker-compose.yaml` files.

**Example from `server-64gb-storage`:**

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical
        snapshots_discover_children: true
```

**What Happens:**

1. Ansible creates `fastpool/compositions` with `policy: critical`
2. Docker Compose applications run and Docker creates child datasets:
   - `fastpool/compositions/jellyfin_config`
   - `fastpool/compositions/immich_pgdata`
   - `fastpool/compositions/gitea_data`
   - ... (dozens more)
3. When `zfs-snapshot` runs, it:
   - Queries ZFS: `zfs list -H -o name -r fastpool/compositions`
   - Discovers all Docker-created children
   - Applies `policy: critical` to each discovered child
   - Creates snapshots for all of them

**Observing Discoveries:**

Use debug mode to see what the scripts discover:

```bash
sudo /opt/zfs-policy/zfs-snapshot --type hourly --dry-run --debug
```

Example output:
```
[DEBUG] Processing dataset: fastpool/compositions (policy: critical, snapshots_discover_children: true)
[DEBUG] Discovered children for fastpool/compositions:
[DEBUG]   - fastpool/compositions/jellyfin_config
[DEBUG]   - fastpool/compositions/immich_pgdata
[DEBUG]   - fastpool/compositions/gitea_data
[DEBUG] Creating snapshot: fastpool/compositions@autosnap_2026-01-22_14:00:00_hourly
[DEBUG] Creating snapshot: fastpool/compositions/jellyfin_config@autosnap_2026-01-22_14:00:00_hourly
[DEBUG] Creating snapshot: fastpool/compositions/immich_pgdata@autosnap_2026-01-22_14:00:00_hourly
...
```

#### When to Use `snapshots_discover_children`

- **Docker volumes** created by the ZFS storage driver
- **Development environments** where datasets are created ad-hoc
- **External snapshots** where other tools create child datasets
- **Dynamic workloads** where dataset structure changes frequently

### Combining Both Features

You can use both `children_inherit_policy` and `snapshots_discover_children` together. This is useful when you have:
- **Declared** children that need different policies (handled by inheritance)
- **Undeclared** children created at runtime (handled by discovery)

**Example:**

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical
        children_inherit_policy: true
        snapshots_discover_children: true
        datasets:
          logs:
            policy: none        # Declared child with override
          # Docker will create many more children at runtime
```

**What Happens:**

1. **Configuration time** (Ansible processes inventory):
   - `fastpool/compositions` → `critical`
   - `fastpool/compositions/logs` → `none` (explicit override)

2. **Runtime** (snapshot scripts execute):
   - Scripts query ZFS and discover: `jellyfin_config`, `immich_pgdata`, `gitea_data`, etc.
   - Discovered children get `critical` (parent's policy)
   - Declared `logs` child gets `none` (already configured)

### Feature Comparison

| Aspect | `children_inherit_policy` | `snapshots_discover_children` |
|--------|------------------|---------------------|
| **When processed** | Configuration time (Ansible) | Runtime (every script execution) |
| **What it affects** | Declared child datasets in inventory | Undeclared datasets found via ZFS query |
| **Primary use case** | Setting defaults for known children | Capturing Docker volumes and dynamic datasets |
| **Overrides** | Children can override with explicit `policy` | No override possible (uses parent's value) |
| **Performance impact** | None (processed once during deployment) | Minimal (one `zfs list` command per parent) |
| **Debugging** | Check Ansible facts/output | Use `--debug --dry-run` on scripts |
| **Requirements** | Child datasets must be declared in inventory | Parent dataset must exist in ZFS |

**Choosing Between Them:**

- When you know what child datasets will exist, and want a default with occasional overrides, use **`children_inherit_policy`**.
- When children are created dynamically, and you want to capture everything, use **`snapshots_discover_children`**.
- When you have a mix of known datasets (with different policies) and unknown datasets, use **both**.

### Troubleshooting

#### Children Not Getting Snapshotted

**Problem:** Child datasets exist, but they do not get snapshots.

**Check:**
1. Does the parent have `snapshots_discover_children: true`? (For undeclared children)
   ```bash
   # Verify with debug mode
   sudo /opt/zfs-policy/zfs-snapshot --type hourly --dry-run --debug | grep "snapshots_discover_children"
   ```

2. Does the parent have `children_inherit_policy: true`? (For declared children)
   ```bash
   # Check the processed policy values
   ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags system-zfs-policy --check --diff
   ```

3. Did the child explicitly set `policy: none`?
   ```yaml
   # This overrides inheritance:
   datasets:
     skip-me:
       policy: none
   ```

#### Too Many Snapshots

**Problem:** Discovery captures datasets that you do not want to snapshot.

**Solution:** Explicitly set `policy: none` on unwanted children:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        policy: critical
        snapshots_discover_children: true
        datasets:
          temp-data:
            policy: none        # Explicitly exclude this one
```

#### Performance with Many Children

**Problem:** You are concerned about performance when the scripts discover hundreds of datasets.

**Reality:** Discovery is very fast. Each `snapshots_discover_children: true` dataset triggers one `zfs list` command, which completes in milliseconds even for hundreds of children. Performance impact is negligible for typical infrastructure (< 100 children per parent).

**Measurement:**
```bash
# Time a discovery operation
time sudo zfs list -H -o name -r fastpool/compositions
```

Typical result: < 50ms for 50+ Docker volumes.

## Policy definitions

Policies control snapshotting and replication. Policies make datasets simpler to configure, and keep the infrastructure consistent.

### ZFS Snapshot and retention

These tables show how each policy influences the snapshot scheduling, retention, and pruning for a dataset.

#### Snapshot Frequency

If `autosnap` is true, `systemd` timers trigger a snapshotting script at these frequencies:

- `Frequently`: The script activates once per minute.
- `Hourly`: The script activates once each hour.
- `Monthly`: The script activates once each month.
- `Yearly`: The script activates once per year.

#### Snapshot Creation

The `autosnap` policy column decides if the scripts create automatic snapshots for a dataset.

If the number in a column is greater than 0, the scripts create a ZFS snapshot at that period.

| Policy ID        | frequently | hourly | monthly | yearly | autosnap | autoprune |
| ---------------- | ---------- | ------ | ------- | ------ | -------- | --------- |
| `none` (default) | 0          | 0      | 0       | 0      | FALSE    | FALSE     |
| `low`            | 0          | 3      | 1       | 0      | TRUE     | TRUE      |
| `high`           | 0          | 24     | 1       | 1      | TRUE     | TRUE      |
| `critical`       | 0          | 36     | 3       | 5      | TRUE     | TRUE      |

#### Snapshot Pruning

A separate script prunes snapshots frequently, so that they do not grow out of control. This script runs only when the dataset's policy sets `autoprune` to true. The script checks each snapshot against the policy table, and destroys or keeps it based on that table. If a column has a number greater than 0, the script keeps that many of the most recent snapshots of that frequency type.

If `autoprune` is false, the script keeps every snapshot.

### ZFS Replication

This table shows how widely each policy replicates snapshots across the infrastructure.

| Policy ID        | Onsite  | Offsite  |
| ---------------- | ------- | -------- |
| `none` (default) | FALSE   | FALSE    |
| `low`            | FALSE   | FALSE    |
| `high`           | TRUE    | FALSE    |
| `critical`       | TRUE    | TRUE     |

- `Onsite`: The main onsite backup host pulls snapshots to itself.
- `Offsite`: The onsite backup host pushes the dataset's snapshots to a remote backup host.

**Onsite** replication hosts are trusted. Datasets on them are encrypted, but the ZFS key stays loaded, so the host can access the datasets.

**Offsite** hosts are not trusted. Datasets backed up to them are encrypted, and the decryption key is not present on the remote host. This protects against data theft, even if someone compromises the offsite host.

## ZFS roles

The following roles form the core of the ZFS snapshot and replication system.

- `backups-zfs-client`
- `backups-zfs-server`
- `backups-zfs-archive-offsite`

A dedicated backup user sends snapshots from clients to the main onsite backup host. A similar user receives snapshots on untrusted offsite hosts.

## Security Model

- Backup user (UID 1099) with restricted SSH (restrict_commands.sh)
- ZFS delegation: only send, snapshot, hold, release, destroy, mount
- Why clients cannot push snapshots (this prevents lateral movement if an attacker compromises a client)
- Tailscale-only network access

## Replication layout - Push vs Pull

This section explains the pull and push replication pattern. By design, other hosts never get the ability to connect directly to the backup host. Instead, the backup host makes an SSH connection to each machine. It either runs `zfs send` on that machine, through a locked-down user, to pull the data to itself, or it runs `zfs receive` and pushes data directly to an offsite host.

## Pools

### Pool Naming conventions

Pool names are typically:

- `fastpool` for SSDs
- `slowpool` for HDDs

### Pool Configuration

You configure a ZFS pool from one or more `vdev` devices. Each `vdev` device uses one or more physical drives.

See the Ansible [zpool documentation](https://docs.ansible.com/projects/ansible/latest/collections/community/general/zpool_module.html#ansible-collections-community-general-zpool-module) for more information.

```yaml
zfs:
  fastpool:
    vdevs:
      - type: mirror
        disks:
          - /dev/disk/by-id/scsi-SATA_CT1000BX500SSD1_2216E629AC18
          - /dev/disk/by-id/scsi-SATA_SanDisk_SDSSDH3_22087N455301
```

or

```yaml
zfs:
  fastpool:
    vdevs:
      - type: mirror
        disks:
          - /dev/sda
          - /dev/sdb
      - type: mirror
        disks:
          - /dev/sdc
          - /dev/sdd
```
