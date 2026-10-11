---
status: accepted
---

# The Offsite copy is a restic repository, filled by the backup server

The design in ADR-0001 sends `critical` datasets off-site with raw `zfs send`
to a ZFS host we control. That host does not exist: the only one died, and a
replacement in a colo or at a friend's house is a budget question
(awfulwoman/meta#6). Until it exists there is no Offsite copy at all. We are
therefore building the Offsite copy with non-ZFS tooling now, and keeping the
ZFS push path (`backups-zfs-archive-offsite`, `zfs-push-backups`) untouched for
the day a ZFS host arrives.

The backup server runs restic against a Hetzner Storage Box over SFTP. It reads
the newest snapshot of each `critical` replica, mounted read-only, and sends it
to one repository.

## Why this shape

- **`critical` is still the only flag.** The targets come from the same
  `zfs_offsite_datasets` filter the ZFS push uses. Nothing new to annotate.
- **The backup server sends, not the service hosts.** It already holds every
  `critical` dataset with its key loaded. Service hosts stay pull-only and never
  hold an offsite credential, which is the property the pull design exists for.
- **restic, not borg.** One repository format covers SFTP and S3, and
  `restic copy` makes a second provider cheap later.
- **Hetzner Storage Box.** Already a vendor, managed by the Terraform we
  already run, priced flat rather than per request, and snapshotted by the
  provider.
- **Provider snapshots, not append-only keys, cover a compromised backup
  server.** The SFTP sub-account can delete the repository, but it cannot
  delete the Storage Box's own snapshots. Those are removed only through the
  Hetzner API.
- **restic encrypts on the backup server.** The Storage Box is untrusted, as
  the ZFS archive host was: it never sees a key or a plaintext byte.

## Consequences

- The Hetzner API token is now able to destroy the Offsite copy and its
  snapshots. It must not be present on the backup server. Today
  `environment_config` writes it to `/etc/environment` on every host, which
  defeats the snapshot cover until that is narrowed to the Terraform host.
- The repository password must exist somewhere that does not depend on this
  infrastructure. The 1Password Connect data on camina is itself in the Offsite
  scope, so a password stored only there is locked inside its own backup.
- The offsite job does not take the host-wide replication lock. The first
  upload is about 1 TB over a 10 Mbit/s uplink, so it runs for more than a
  week. A pull that waits more than 90 minutes for the lock gives up, so a
  shared lock would stop local replication for that whole time. The job reads a
  held snapshot at idle priority instead.
- A restore is a file restore, not a `zfs receive`. Snapshot history, dataset
  properties and the dataset tree are not in the Offsite copy. Each target
  restores as a directory, per client and dataset.
- Databases are crash-consistent only, exactly as the replicas are. Logical
  dumps before the snapshot would fix both copies at once and are still open.
- Offsite scope now costs upload time as well as money. A `critical` dataset
  that churns is paid for twice.
- When a ZFS offsite host exists, decide whether this becomes a second
  provider or is retired. Nothing here blocks either.
