# ZFS Architecture

ZFS is the filesystem of choice for storing important, non-operating system data. All ZFS storage is configured via Ansible roles.

## Defining ZFS configuration

The ZFS configuration for each host are stored in a `zfs` dictionary item. It defines both pools and datasets.

Example:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
  slowpool:
    datasets:
      shared:
        datasets:
          syncthing:
    encrypteddataset:
      importance: critical
      properties:
        encryption: aes-256-gcm
        keylocation: "{{ vault_zfs_default_encryption_passphrase_path }}"
        keyformat: passphrase
```

The top level items immediately underneath the `zfs` key are ALWAYS pool names.

A pool's datasets are defined immediately below the pool with the `datasets` key.

Each dataset can have further child datasets defined. They also use the `datasets` key.

## Policy-driven snapshots and replication

ZFS snapshotting and replication in this infrastructure is policy-driven. This means that policies are defined and then applied to datasets. Policies are assigned to datasets using the `importance` key.

Relevant roles:

- `system-zfs`: configures ZFS on a host by reading the `zfs` dictionary variable and creating the defined pools and datasets.
- `system-zfs-policy`: sets up a hosts's ZFS snapshots via the policy system.
- `backups-zfs-server`: configures a host that replicates snapshots to itself via a pull mechanism. At least one host with this role is critical for backup operations.
- `backups-zfs-client`: configures a host to enable hosts configured with `backups-zfs-server` to _pull__ dataset snapshots from it.
- `backups-zfs-offsite`: configures a host to enable hosts configured with `backups-zfs-server` to _push_ datasets snapshots to it.

## Advanced Dataset Policy Management

ZFS policy management includes two powerful features for managing dataset importance at scale: **policy inheritance** and **runtime child discovery**. These features solve different but complementary problems in infrastructure management.

### Policy Inheritance with `children_inherit_policy`

Policy inheritance is a **configuration-time** feature that allows parent datasets to automatically pass their importance value to child datasets declared in your Ansible inventory.

#### How It Works

When a dataset has `children_inherit_policy: true`, all its child datasets automatically inherit the parent's importance level **unless** they explicitly define their own importance. This inheritance happens during Ansible's configuration processing, before any scripts run.

#### Use Case: Mixed-Priority Docker Compose Applications

A common scenario is a parent dataset containing multiple Docker Compose applications, where most should be backed up at the parent's level, but some specific ones need different treatment.

**Example from `dns` host:**

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
        children_inherit_policy: true
        datasets:
          awfulwoman:
            importance: none        # Explicitly override to skip backups
          container-management:
            importance: none        # Explicitly override to skip backups
          reverseproxy:
            importance: none        # Explicitly override to skip backups
          # Other compositions inherit 'critical' automatically
```

**What Happens:**

- `fastpool/compositions` is marked `critical` with `children_inherit_policy: true`
- `fastpool/compositions/awfulwoman` explicitly sets `importance: none` → gets `none` (override)
- `fastpool/compositions/container-management` explicitly sets `importance: none` → gets `none` (override)
- `fastpool/compositions/reverseproxy` explicitly sets `importance: none` → gets `none` (override)
- Any other composition datasets declared would inherit `critical` from their parent

This pattern is cleaner than explicitly setting `importance: critical` on every composition dataset.

#### When to Use `children_inherit_policy`

- **Docker Compose parent datasets** where most containers should have the same backup level
- **Media libraries** with consistent importance (e.g., all music folders are critical, all TV shows are low)
- **Shared datasets** where you want a default policy but occasional overrides
- **Development environments** with a baseline policy and specific exceptions

### Runtime Child Discovery with `snapshots_discover_children`

Runtime child discovery is a **runtime** feature that enables automatic discovery and policy application to dynamically-created child datasets that aren't declared in your Ansible inventory.

#### How It Works

When a dataset has `snapshots_discover_children: true`, the snapshot and pruning scripts query ZFS at runtime to find all child datasets that actually exist on the system. Discovered children automatically receive the same importance policy as their parent.

This happens every time the scripts run, meaning newly-created children are immediately included in the next snapshot cycle.

#### Use Case: Docker Volume Discovery

Docker automatically creates ZFS datasets for volumes when using the ZFS storage driver. These datasets aren't in your inventory because Docker creates them dynamically based on `docker-compose.yaml` files.

**Example from `host-storage`:**

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
        snapshots_discover_children: true
```

**What Happens:**

1. Ansible creates `fastpool/compositions` with `importance: critical`
2. Docker Compose applications run and Docker creates child datasets:
   - `fastpool/compositions/jellyfin_config`
   - `fastpool/compositions/immich_pgdata`
   - `fastpool/compositions/gitea_data`
   - ... (dozens more)
3. When `zfs-snapshot` runs, it:
   - Queries ZFS: `zfs list -H -o name -r fastpool/compositions`
   - Discovers all Docker-created children
   - Applies `importance: critical` to each discovered child
   - Creates snapshots for all of them

**Observing Discoveries:**

Use debug mode to see what gets discovered:

```bash
sudo /opt/zfs-policy/zfs-snapshot --type hourly --dry-run --debug
```

Example output:
```
[DEBUG] Processing dataset: fastpool/compositions (importance: critical, snapshots_discover_children: true)
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
        importance: critical
        children_inherit_policy: true
        snapshots_discover_children: true
        datasets:
          logs:
            importance: none        # Declared child with override
          # Docker will create many more children at runtime
```

**What Happens:**

1. **Configuration time** (Ansible processes inventory):
   - `fastpool/compositions` → `critical`
   - `fastpool/compositions/logs` → `none` (explicit override)

2. **Runtime** (snapshot scripts execute):
   - Scripts query ZFS and discover: `jellyfin_config`, `immich_pgdata`, `gitea_data`, etc.
   - Discovered children get `critical` (parent's importance)
   - Declared `logs` child gets `none` (already configured)

### Feature Comparison

| Aspect | `children_inherit_policy` | `snapshots_discover_children` |
|--------|------------------|---------------------|
| **When processed** | Configuration time (Ansible) | Runtime (every script execution) |
| **What it affects** | Declared child datasets in inventory | Undeclared datasets found via ZFS query |
| **Primary use case** | Setting defaults for known children | Capturing Docker volumes and dynamic datasets |
| **Overrides** | Children can override with explicit `importance` | No override possible (uses parent's value) |
| **Performance impact** | None (processed once during deployment) | Minimal (one `zfs list` command per parent) |
| **Debugging** | Check Ansible facts/output | Use `--debug --dry-run` on scripts |
| **Requirements** | Child datasets must be declared in inventory | Parent dataset must exist in ZFS |

**Choosing Between Them:**

- **Use `children_inherit_policy`** when you know what child datasets will exist and want to set a default with occasional overrides
- **Use `snapshots_discover_children`** when children are created dynamically and you want to capture everything
- **Use both** when you have a mix of known (with varying importance) and unknown children

### Troubleshooting

#### Children Not Getting Snapshotted

**Problem:** Child datasets exist but aren't getting snapshots.

**Check:**
1. Does the parent have `snapshots_discover_children: true`? (For undeclared children)
   ```bash
   # Verify with debug mode
   sudo /opt/zfs-policy/zfs-snapshot --type hourly --dry-run --debug | grep "snapshots_discover_children"
   ```

2. Does the parent have `children_inherit_policy: true`? (For declared children)
   ```bash
   # Check the processed importance values
   ansible-playbook ansible/playbooks/baremetal/core.yaml --tags system-zfs-policy --check --diff
   ```

3. Did the child explicitly set `importance: none`?
   ```yaml
   # This overrides inheritance:
   datasets:
     skip-me:
       importance: none
   ```

#### Too Many Snapshots

**Problem:** Discovery is capturing datasets you don't want snapshotted.

**Solution:** Explicitly set `importance: none` on unwanted children:

```yaml
zfs:
  fastpool:
    datasets:
      compositions:
        importance: critical
        snapshots_discover_children: true
        datasets:
          temp-data:
            importance: none        # Explicitly exclude this one
```

#### Performance with Many Children

**Problem:** Concerned about performance when discovering hundreds of datasets.

**Reality:** Discovery is very fast. Each `snapshots_discover_children: true` dataset triggers one `zfs list` command, which completes in milliseconds even for hundreds of children. Performance impact is negligible for typical infrastructure (< 100 children per parent).

**Measurement:**
```bash
# Time a discovery operation
time sudo zfs list -H -o name -r fastpool/compositions
```

Typical result: < 50ms for 50+ Docker volumes.

## Policy definitions

By defining policies that dictate snapshotting and replication we make it easier to configure datasets, and increase consistency across the infrastructure.

### ZFS Snapshot and retention

These tables show how each policy influences the snapshot scheduling, retention, and pruning for a dataset.

#### Snapshot Frequency

If `autosnap` is true then `systemd` timers will trigger a snapshotting script at the following frequencies.

- `Frequently`: The script activates once per minute.
- `Hourly`: The script activates once each hour.
- `Monthly`: The script activates once each month.
- `Yearly`: The script activates once per year.

#### Snapshot Creation

The policy column `autosnap` dictates if the automatic snapshotting should even run on a dataset.

If the number in a column is greater than 0 then a ZFS snapshot should be created at that period.

| Policy ID        | frequently | hourly | monthly | yearly | autosnap | autoprune |
| ---------------- | ---------- | ------ | ------- | ------ | -------- | --------- |
| `none` (default) | 0          | 0      | 0       | 0      | FALSE    | FALSE     |
| `low`            | 0          | 3      | 1       | 0      | TRUE     | TRUE      |
| `high`           | 0          | 24     | 1       | 1      | TRUE     | TRUE      |
| `critical`       | 0          | 36     | 3       | 5      | TRUE     | TRUE      |

#### Snapshot Pruning

Snapshots should be pruned, lest they grow out of control. A separate script should run frequently to do this. It should only run if the policy for that datasets has `autoprune` set to true. It should check against a representation of the policy table to see if any snapshot should be destroyed or kept. If a column has a number is greater than 0 then that number of the most recent snapshots of that frequency type should be retained.

If `autoprune` is false then all created snapshots should be retained.

### ZFS Replication

This table shows how each policy dictates how widely snapshots are replicated across the infrastructure.

| Policy ID        | Onsite  | Offsite  |
| ---------------- | ------- | -------- |
| `none` (default) | FALSE   | FALSE    |
| `low`            | FALSE   | FALSE    |
| `high`           | TRUE    | FALSE    |
| `critical`       | TRUE    | TRUE     |

- `Onsite`: Snapshots are replicated to the main onsite backup host via a pull action.
- `Offsite`: Snapshots of that dataset on the backup host are _push_ replicated to a remote backup host.

**Onsite** replication hosts are trusted. Datasets on them are encrypted, but the ZFS key is loaded, allowing datasets to be accessed.

**Offsite** hosts are not trusted, and as such the datasets backed up to them are encrypted but the decryption key is not present on the remote host. This provides protection against data theft even if the offsite host is compromised.

## ZFS roles

The following roles form the core of the ZFS snapshot and replication system.

- `backups-zfs-client`
- `backups-zfs-server`
- `backups-zfs-archive-offsite`

A dedicated backup user is used to send snapshots from clients to the main onsite backup host. A similar user is used to receive snapshots on untrusted offsite hosts.

## Security Model

- Backup user (UID 1099) with restricted SSH (restrict_commands.sh)
- ZFS delegation: only send, snapshot, hold, release, destroy, mount
- Why clients can't push (prevents lateral movement if compromised)
- Tailscale-only network access

## Replication layout - Push vs Pull

Note the _pulling_ and _pushing_ of datasets. The other hosts are deliberately never given the ability to directly connect to the backup host. Instead the backup host performs an SSH connection to each machine and either initiates a `zfs send` from that machine to itself using a locked-down user, or starts `zfs receive` and pushes directly to an off-site host.

## Pools

### Pool Naming conventions

Pool names are typically:

- `fastpool` for SSDs
- `slowpool` for HDDs

### Pool Configuration

ZFS pools are configured from one of more `vdev` devices. These `vdev` devices are formed from one or more physical drives.

See the Ansible [zpool documentation](https://docs.ansible.com/projects/ansible/latest/collections/community/general/zpool_module.html#ansible-collections-community-general-zpool-module) for more info.

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
