# Infrastructure Work Log

This log tracks significant changes, decisions, and progress across work sessions for the infra repository.

---

## December 31, 2025 - ZFS Push Backup Implementation

**Session Overview**: Created a new push-based ZFS backup script to send datasets from the backup server to an offsite remote server (host-albion), enabling bidirectional backup capabilities.

### What Was Done

- **Created new push backup script** (`ansible/roles/server-zbackups-new/templates/zfs-push-backups.py`):
  - Based on existing `zfs-pull-backups.py` but reverses direction: local send, remote receive
  - Added `-w` flag to all `zfs send` commands to support raw/encrypted dataset transfers
  - Implemented `--strip-prefix` argument (defaults to `{{ zfsbackup_dataset }}`) to simplify remote dataset paths
  - Added `ensure_remote_parent_exists()` function that creates parent datasets on remote using `zfs create -p`
  - Remote path transformation: strips local backup prefix so `backuppool/encryptedbackups/host-storage/...` becomes `host-storage/...` on remote
  - Handles both initial sync (full + incremental) and subsequent syncs (incremental only) like the pull script

- **Updated ZFS delegation permissions** in `ansible/roles/server-zbackups-new/tasks/main.yaml`:
  - Added `send` permission to the delegation list for the backup user
  - Template deployment was already configured to deploy both pull and push scripts

- **Investigated remote permission requirements**:
  - Identified that source datasets need `send` and `hold` permissions (now configured)
  - Identified that remote destination needs `create`, `mount`, and `receive` permissions
  - Started but reverted changes to `client-zbackups` role - approach needs reconsideration

### Key Decisions

- **Path stripping for cleaner remote structure**: Rather than replicating the full local path (e.g., `backuppool/encryptedbackups/host-storage/tank/data`), the script strips the backup pool prefix to create a cleaner remote hierarchy (`host-storage/tank/data`)

- **Automatic parent dataset creation**: The script ensures all parent datasets exist on the remote before attempting to receive snapshots, preventing errors from missing intermediate datasets

- **Raw encrypted transfers**: Using `-w` flag ensures encrypted datasets are sent in their raw encrypted form, maintaining encryption at rest on the offsite server without needing the encryption key there

- **Deferred remote permission configuration**: Rather than immediately implementing remote permissions via the `client-zbackups` role, decided to pause and rethink the approach for managing ZFS receive permissions on the offsite server

### Files Changed

- `ansible/roles/server-zbackups-new/templates/zfs-push-backups.py` (new file, ~250 lines)
- `ansible/roles/server-zbackups-new/tasks/main.yaml` (added `send` to ZFS delegation)

### Current State

- Push script is functionally complete and ready for testing
- Local (backup server) has necessary `send` permissions configured
- Remote (host-albion) still needs ZFS receive permissions configured before script can be tested end-to-end
- Changes are uncommitted in git

### Next Steps

1. **Determine remote permission strategy**:
   - Decide how to manage ZFS permissions on host-albion (offsite server)
   - Consider whether to extend `client-zbackups` role or create a new role
   - Determine what user should have receive permissions on remote

2. **Configure remote permissions**:
   - Set up `create`, `mount`, `receive` permissions on host-albion for the receiving dataset
   - Ensure SSH key-based authentication is configured between backup server and host-albion

3. **Test push workflow**:
   - Run initial push to verify full + incremental sync works
   - Test subsequent runs to verify incremental-only syncs work
   - Verify encrypted datasets remain encrypted on remote
   - Test with multiple datasets to ensure path stripping works correctly

4. **Integration**:
   - Add push backups to scheduled cron jobs alongside pull backups
   - Consider timing: should push happen after pull, or separately?
   - Add monitoring/alerting for push backup failures

### Notes

- The push script mirrors the pull script's logic for determining initial vs. subsequent syncs
- Remote datasets will have a cleaner hierarchy since the backup pool prefix is stripped
- The `-w` (raw) flag is critical for maintaining encryption without exposing keys to the remote
- Both scripts now deployed by the same template task in the role, keeping them in sync
- This enables a multi-tier backup strategy: remote servers → backup server → offsite server

### Code Snippets

**Path stripping logic**:
```python
parser.add_argument('--strip-prefix', default='{{ zfsbackup_dataset }}',
                    help='Prefix to strip from local dataset path for remote path')

# Later in code:
remote_dataset = local_dataset.replace(strip_prefix + '/', '', 1)
```

**Raw encrypted send**:
```python
# All zfs send commands now use -w flag
subprocess.run(['zfs', 'send', '-w', f'{dataset}@{earliest}'], ...)
subprocess.run(['zfs', 'send', '-w', '-I', f'@{earliest}', f'{dataset}@{latest}'], ...)
```

**Ensuring remote parent exists**:
```python
def ensure_remote_parent_exists(remote_user, remote_host, remote_dataset):
    parent = remote_dataset.rsplit('/', 1)[0]
    ssh_cmd = ['ssh', f'{remote_user}@{remote_host}',
               'zfs', 'create', '-p', parent]
    subprocess.run(ssh_cmd, check=False)  # Ignore if already exists
```

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
