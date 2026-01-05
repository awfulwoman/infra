# ZFS Architecture

ZFS is the filesystem of choice for storing important, non-operating system data. All ZFS storage is configured via Ansible roles.

## Definitions

The ZFS configuration for each stored in a `zfs` dictionary item. It defines pools and datasets.

Here is an example:

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

The top level items underneath the `zfs` item are always pool names.

Below each pool datasets are defined with the `dataset` item.

## Snapshots

ZFS in this infrastructure is policy-driven. This means that policies are defined and then applied to datasets. Policies are assigned to datasets using the `importance` item.

- `none` (default): this dataset will not have snapshots enabled and will not be pulled to the central backup server.
- `low`: this dataset will enable daily snapshots and retain them for one week. The dataset and all snapshots will be pulled to the central backup server.
- `critical`: this dataset will enable more frequent snapshots and will retain them for a longer duration. The dataset and all snapshots will be pulled to the central backup server, and from there pushed to one or more off-site backup locations.

The `system-zfs` Ansible role reads the contents of a hosts `zfs` dictionary and creates pools and datasets.

Another, as yet unbuilt role (likely to be called `system-zfs-policy`), wil set up ZFS snapshots via the policy system.

`sanoid` is currently being used for policy setting but will soon be removed, in favour of the new role.

## Policy definitions

| Policy ID  | Frequently | Hourly | Monthly | Yearly | Autosnap | Autoprune |
| ---------- | ---------- | ------ | ------- | ------ | -------- | --------- |
| `none`     | 0          | 0      | 0       | 0      | FALSE    | FALSE     |
| `low`      | 0          | 3      | 1       | 0      | TRUE     | TRUE      |
| `high`     | 0          | 24     | 1       | 1      | TRUE     | TRUE      |
| `critical` | 0          | 36     | 3       | 5      | TRUE     | TRUE      |

## Replication

The infra uses a three-tier backup system (local snapshots → central backup server → encrypted off-site archive), importance-based policies, and a zero-trust off-site model where encryption keys are never loaded on remote hosts.

The following roles form the core of the ZFS backup and replication system.

- `backups-zfs-client`
- `backups-zfs-server`
- `backups-zfs-archive-offsite`

A dedicated backup user is used to transmit snapshots.

### Security Model

- Backup user (UID 1099) with restricted SSH (restrict_commands.sh)
- ZFS delegation: only send, snapshot, hold, release, destroy, mount
- Why clients can't push (prevents lateral movement if compromised)
- Tailscale-only network access

### Push vs Pull

Note the _pulling_ and _pushing_ of datasets. The other hosts are deliberately never given the ability to directly connect to the backup host. Instead the backup host performs an SSH connection to each machine and either initiates a `zfs send` from that machine to itself using a locked-down user, or starts `zfs receive` and pushes directly to an off-site host.

## Naming conventions

Pool names are typically:

- `fastpool` for SSDs
- `slowpool` for HDDs
