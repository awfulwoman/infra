# ZFS Backups

This role sets this host as a backup server. It allows ZFS datasets to be _pushed_ and/or _pulled_ to and from hosts configured with `client-zbackups`. The newly configured backup host thus acts as the controller for ZFS backups, enabling the pulling of datasets from other hosts to its own encrypted datasets, and pushing those encrypted off-site to potentially less trusted hosts.

Note the _pulling_ and _pushing_ of datasets. The other hosts are deliberately never given the ability to directly connect to the backup host. Instead the backup host performs an SSH connection to each machine and either initiates a `zfs send` from that machine to itself using a locked-down user, or starts `zfs receive` and pushes directly to an off-site host.
