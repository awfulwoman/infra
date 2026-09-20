---
status: accepted
---

# A dataset's policy is the single flag for retention and replication

A dataset's `policy` already decided three separate things: how long snapshots
are kept (`zfs_datasets_with_policy`), whether the backup server pulls it
(`zfs_backup_datasets`, `high` and `critical`), and whether it goes off-site
(`zfs_offsite_datasets`, `critical` only). We are making that ladder explicit
and relying on it, rather than adding a second flag beside it:

    none      no snapshots, so no replication is possible
    low       snapshots kept locally only
    high      also pulled to the backup server
    critical  also pushed off-site

A future non-ZFS off-site tool keys off the same `critical` value, so the
question "what is precious?" is answered in one place, next to the data.

## The default is inverted, and every composition must state its policy

`<pool>/compositions` is `low`, and each composition states its own policy.
Previously the parent was `critical` and everything Docker created inherited it.

That old default was fail-safe: forgetting to declare something meant it was
over-protected. The new default is not, so a composition with no stated policy
is a hard error rather than a silent `low`. The typing is the point — it forces
a deliberate answer for each service instead of sweeping everything into
`critical` and paying to snapshot and replicate caches, logs and rebuildable
indexes. Retention and replication only become a truthful statement about what
matters if each entry was actually decided.

## Consequences

- Policy resolution had to become identical across all three filters. The
  replication filters read only a stated `policy:` key and ignored
  `children_inherit_policy`, so a child that inherited `critical` was silently
  not replicated. No host hit this — the flag was only ever set on datasets
  with no declared children — but the ladder does not hold without the fix.
- Downgrading a child now genuinely excludes it from replication. Under the old
  arrangement the backup server pulled the parent recursively, so a child at
  `low` was still fully replicated; its policy only shortened local retention.
- Runtime-discovered children (`snapshots_discover_children`) still inherit
  from the parent, which is now `low`. Anything Docker creates and nobody
  declares is snapshotted briefly and never replicated. Orphaned datasets
  therefore stop accruing cost on their own, but still need deleting.
