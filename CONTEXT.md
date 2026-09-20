# Infra

Ansible-managed infrastructure across the home fleet and a few remote hosts, including how data is protected.

## Language

**Composition**:
One Docker Compose application, declared in a host's `compositions:` list and given its own ZFS dataset under `<pool>/compositions`.

**Orphan dataset**:
A dataset under `<pool>/compositions` with no matching entry in that host's `compositions:` list. It is created by Docker, never removed when the composition is retired, and keeps inheriting the parent's snapshot policy. Its cost is almost entirely snapshots.
_Avoid_: Stale dataset, leftover

**Churn dataset**:
A dataset whose live data is small but which is rewritten constantly, so each snapshot pins a fresh copy. Monitoring, logging and recorder databases are the usual case. It needs a lower policy than its importance suggests.

**Backup server**:
The one host that pulls ZFS snapshots from every other host into an encrypted dataset. Currently ambiguous: two hosts hold the role.
_Avoid_: Backup host, backup controller

**Offsite copy**:
A copy of selected data held outside the building, to survive loss of the whole site. None exists today.
_Avoid_: Remote backup, cloud backup

**Offsite scope**:
The data chosen to reach the Offsite copy. Narrower than the data that is snapshotted, because offsite storage is paid for per byte.
