# Infrastructure Work Log

This log tracks significant changes, decisions, and progress across work sessions for the infra repository.

---

## December 30, 2025 - ZFS Backup Script Refactor

**Session Overview**: Completely rewrote the ZFS pull backup script to properly handle both initial and subsequent sync operations with correct permission delegation.

### What Was Done

- **Refactored ZFS backup script** (`ansible/roles/server-zbackups-new/templates/zfs-pull-backups.py`):
  - Rewrote sync logic to handle two distinct scenarios:
    - **Initial sync**: Sends earliest snapshot as full backup, then incremental to latest
    - **Subsequent sync**: Finds latest common snapshot between local/remote, does incremental send
  - Added three new helper functions for cleaner code organization:
    - `get_remote_snapshots()`: Lists all snapshots on remote host
    - `get_local_snapshots()`: Lists all snapshots on local dataset
    - `send_and_receive()`: Handles the actual ZFS send/receive pipeline
  - Improved error handling and logging throughout

- **Fixed ZFS delegation permissions** in `ansible/roles/server-zbackups-new/tasks/main.yaml`:
  - Added `xattr` and `acltype` to delegated permissions list
  - This resolved permission errors when receiving snapshots

### Key Decisions

- **Two-phase approach for syncing**: Rather than always sending all snapshots incrementally, the script now intelligently determines whether it's an initial sync or continuation:
  - Checks if local dataset exists and has snapshots
  - If empty or doesn't exist: does initial sync (earliest full + incremental to latest)
  - If exists with snapshots: finds common ground and does incremental from there

- **Common snapshot detection**: Uses `common_snapshots[-1]` to find the most recent common snapshot between local and remote, ensuring minimal data transfer on subsequent syncs

### Files Changed

- `ansible/roles/server-zbackups-new/templates/zfs-pull-backups.py` - Complete rewrite of sync logic
- `ansible/roles/server-zbackups-new/tasks/main.yaml` - Added `xattr,acltype` to ZFS delegation permissions

### Current State

- Script is tested and working for both initial and subsequent backup runs
- Permission issues resolved with proper delegation
- Code is more maintainable with helper functions separating concerns
- Changes are uncommitted (files show as modified in git status)

### Next Steps

1. **Test edge cases**:
   - What happens if remote has new snapshots but local has snapshots not on remote?
   - Test with multiple datasets
   - Verify behavior when snapshots are manually deleted

2. **Consider adding**:
   - Logging to file in addition to stdout
   - Email notifications on success/failure
   - Metrics/monitoring integration
   - Retention policy handling (old snapshot cleanup)

3. **Deploy and monitor**:
   - Commit changes when satisfied with testing
   - Roll out to production backup systems
   - Monitor first few backup runs for issues

### Notes

- The script assumes snapshots are named with timestamps and can be sorted chronologically
- ZFS delegation requires specific permissions: `send,receive,create,mount,destroy,snapshot,hold,release,clone,promote,rename,xattr,acltype`
- The backup user needs proper SSH key-based auth configured to the remote hosts
- This is part of the `server-zbackups-new` role which appears to be a revised version of backup infrastructure

### Code Snippets

**Common snapshot detection logic**:
```python
common_snapshots = sorted(set(local_snapshots) & set(remote_snapshots))
if common_snapshots:
    latest_common = common_snapshots[-1]  # Most recent common snapshot
    # Do incremental from latest_common to latest_remote
```

**Permission delegation in Ansible**:
```yaml
zfs allow {{ user }} send,receive,create,mount,destroy,snapshot,hold,release,clone,promote,rename,xattr,acltype {{ item }}
```
