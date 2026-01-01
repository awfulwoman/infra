# ZFS Backups

This role sets this host as a backup server. It allows ZFS datasets to be _pushed_ and/or _pulled_ to and from hosts configured with `backups-zfs-client`. The newly configured backup host thus acts as the controller for ZFS backups, enabling the pulling of datasets from other hosts to its own encrypted datasets, and pushing those encrypted off-site to potentially less trusted hosts.

## Push vs Pull

Note the _pulling_ and _pushing_ of datasets. The other hosts are deliberately never given the ability to directly connect to the backup host. Instead the backup host performs an SSH connection to each machine and either initiates a `zfs send` from that machine to itself using a locked-down user, or starts `zfs receive` and pushes directly to an off-site host.

## Policy-driven backups

In a host's `zfs` config each and every dataset can have the `importance` attribute marked. This indicates how to handle the backup and retention of that dataset.

- `none` (default): this dataset will not have snapshots enabled and will not be pulled to the central backup server.
- `low`: this dataset will enable daily snapshots and retain them for one week. The dataset and all snapshots will be pulled to the central backup server.
- `critical`: this dataset will enable hourly snapshots and will retain them on a weekly, monthly, and year basis. The dataset and all snapshots will be pulled to the central backup server, and from there pushed to one or more off-site backup locations.
