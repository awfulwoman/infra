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

This table shows how each each policy dictates how widely snapshots are replicated across the infrastructure.

| Policy ID        | Primary | Secondary | Offsite  |
| ---------------- | ------- | --------- | -------- |
| `none` (default) | FALSE   | FALSE     | FALSE    |
| `low`            | TRUE    | FALSE     | FALSE    |
| `high`           | TRUE    | TRUE      | TRUE     |
| `critical`       | TRUE    | TRUE      | TRUE     |

- `Primary`: Snapshots are replicated to the main onsite backup host via a pull action.
- `Secondary`: Snapshots of that dataset on the backup host are _push_ replicated to a secondary onsite backup host.
- `Offsite`: Snapshots of that dataset on the backup host are _push_ replicated to a remote backup host.

Onsite replication hosts are trusted. Datasets on them are encrypted, but the ZFS key is loaded, allowing datasets to be accessed.

Remote host are not trusted, and as such the datasets backed up to them are encrypted but the decryption key is not present on the remote shosterver.

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

```yaml
zfs:
  fastpool:
    vdevs:
      - type: mirror
        drives: 
          - id: /dev/disk/by-id/scsi-SATA_CT1000BX500SSD1_2216E629AC18
          - id: /dev/disk/by-id/scsi-SATA_SanDisk_SDSSDH3_22087N455301
```
