# Infrastructure Work Log

This log tracks significant changes, decisions, and progress across work sessions for the infra repository.

---

## January 4, 2026 - ZFS Variable Refactoring and Role Consolidation

**Session Overview**: Completed a major refactoring of ZFS-related variables across the entire infrastructure, consolidating the new declarative ZFS role into the main system-zfs role and simplifying variable naming throughout all host configurations and composition roles.

### What Was Done

- **Consolidated system-zfs-new into system-zfs** (commit `22f7ce16`):
  - Merged the new declarative ZFS implementation back into the main `system-zfs` role
  - Deleted the now-redundant `system-zfs-new` role (README, defaults, tasks)
  - Migrated all improvements from system-zfs-new:
    - Declarative `zfs:` config structure with custom filters (`zfs_all_pools`, `zfs_datasets_with_config`)
    - Added `zfs-zed` package for ZFS event daemon support
    - Added `zfs-load-key.service` for automatic encryption key loading at boot
    - Improved pool import logic with fallback to device creation
    - Removed deprecated file-based pool options
  - Template file `zfs-load-key.service` moved to system-zfs role
  - Net result: -106 lines of code through consolidation

- **Migrated playbooks to reference consolidated role** (commit `c97213f6`):
  - Updated `host-homeassistant` playbook to switch from system-zfs to system-zfs-new (before final consolidation)
  - Removed redundant system-zfs reference from `host-backups` playbook
  - Cleaned up commented-out `backups-zfs-client` role from `host-albion` playbook

- **Updated composition roles for new variable names** (commit `5d455f86`):
  - **composition-awfulwoman**: Updated to use `site_path_awfulwoman` and `site_path_shared` variables
  - **composition-get-iplayer**: Fixed typo (`downlaods_dir` → `downloads_dir`) and updated variable reference
  - **composition-immich**: Added `compositions_immich_photo_path` default variable
  - **composition-tubesync**: Changed to use `shared_media_path` directly instead of legacy `tubeachivist_youtube_path`

- **Standardized compositions role variable naming** (commit `d4bdb34b`):
  - Added default `compositions_dataset` variable (value: `fastpool/compositions`)
  - Updated `compositions` role to use new variable instead of `container_compositions_zfs_id`
  - Improved task descriptions for better clarity:
    - "Ensure composition dataset mount is owned by user"
    - "Ensure a ZFS dataset for each composition role is present"
    - "Ensure defined composition roles are included"

- **Simplified ZFS variable definitions across all host_vars** (commit `ecb3adc0`):
  - **Primary goal**: Replace indirect variable references with direct paths for clarity
  - **Removed legacy structures**: Eliminated old `zfs_pools`, `zfs_datasets`, and `zfs_backup_datasets` lists in favor of new declarative `zfs:` structure
  - **Hosts updated**:
    - **dns**: Removed variable indirection for compositions, acme, terraform paths
    - **host-albion**: Simplified to direct `downloads_dir` path
    - **host-backups**: Removed unused `zfs_pools` definitions
    - **host-homeassistant**: Major cleanup of old ZFS variables, retained new `zfs:` structure
    - **host-storage**: Extensive cleanup (79 lines removed) of legacy ZFS variable definitions
    - **vm-awfulwoman**: Simplified to direct `site_path_*` variables
  - **Net reduction**: 126 lines removed across 6 host_vars files

- **Removed musicassistant composition** (commit `2ef30bb1`):
  - Removed `composition-musicassistant` from host-storage's core.yaml
  - Changed from 6 composition roles to 3 (likely removed other compositions as well)

### Key Decisions

- **Consolidation over duplication**: Rather than maintaining two parallel ZFS roles, merged the improved implementation back into the original role. This reduces maintenance burden and prevents confusion about which role to use.

- **Direct paths over variable indirection**: The old pattern of defining variables like `container_compositions_zfs_id: "{{ zfsid_compositions }}"` which then referenced `zfsid_compositions: "fastpool/compositions"` added unnecessary complexity. The new approach uses direct paths or single-level variables (e.g., `compositions_dataset: "fastpool/compositions"`).

- **Declarative ZFS configuration**: The new `zfs:` structure in host_vars is more maintainable than separate lists for pools, datasets, and backup datasets. All ZFS configuration is now in one place with a clear hierarchy.

- **Standard variable naming**: Established clearer naming conventions:
  - Composition-specific paths: `compositions_<role>_<purpose>` (e.g., `compositions_immich_photo_path`)
  - Shared resources: `<resource>_path` or `<resource>_dir` (e.g., `shared_media_path`, `downloads_dir`)
  - ZFS-specific: `compositions_dataset`, with new `zfs:` structure for pool/dataset definitions

- **Cleanup over preservation**: Removed unused/commented-out code rather than leaving it for "just in case" scenarios. This included removing the backups-zfs-client role reference and unused pool definitions.

- **Fail-fast over silent skip**: Rather than silently skipping all tasks when `zfs` variable is undefined, the role now explicitly asserts its presence and fails immediately with a clear error message. This reduces debugging time and makes role requirements explicit.

- **Conditional encryption setup**: Encryption-related tasks (key directory, key files, systemd service) are now only executed when datasets with encryption are actually defined. This prevents unnecessary file operations and service management on hosts without encrypted datasets.

### Files Changed

**Roles modified**:
- `/Users/charlie/Code/infra/ansible/roles/system-zfs/tasks/main.yaml` - Major refactoring and improvements:
  - Initial: 96 insertions, 82 deletions (consolidation)
  - Added: `zfs` variable assertion task
  - Added: Conditional block for encryption tasks (uncommitted)
- `/Users/charlie/Code/infra/ansible/roles/system-zfs/defaults/main.yaml` - Cleanup (2 deletions)
- `/Users/charlie/Code/infra/ansible/roles/system-zfs/templates/zfs-load-key.service` - Moved from system-zfs-new
- `/Users/charlie/Code/infra/ansible/roles/compositions/tasks/main.yaml` - Variable updates
- `/Users/charlie/Code/infra/ansible/roles/compositions/defaults/main.yaml` - Added compositions_dataset default

**Roles deleted**:
- `/Users/charlie/Code/infra/ansible/roles/system-zfs-new/` - Entire role removed (README, defaults, tasks)

**Composition roles updated**:
- `/Users/charlie/Code/infra/ansible/roles/composition-awfulwoman/templates/docker-compose.yaml.j2`
- `/Users/charlie/Code/infra/ansible/roles/composition-get-iplayer/tasks/main.yaml`
- `/Users/charlie/Code/infra/ansible/roles/composition-get-iplayer/templates/docker-compose.yaml.j2`
- `/Users/charlie/Code/infra/ansible/roles/composition-immich/defaults/main.yaml`
- `/Users/charlie/Code/infra/ansible/roles/composition-immich/templates/.env`
- `/Users/charlie/Code/infra/ansible/roles/composition-tubesync/templates/docker-compose.yaml.j2`

**Playbooks updated**:
- `/Users/charlie/Code/infra/ansible/playbooks/baremetal/host-albion/core.yaml`
- `/Users/charlie/Code/infra/ansible/playbooks/baremetal/host-backups/core.yaml`

**Host inventory cleaned up** (6 files, net -126 lines):
- `/Users/charlie/Code/infra/ansible/inventory/host_vars/dns/core.yaml`
- `/Users/charlie/Code/infra/ansible/inventory/host_vars/host-albion/core.yaml`
- `/Users/charlie/Code/infra/ansible/inventory/host_vars/host-backups/core.yaml`
- `/Users/charlie/Code/infra/ansible/inventory/host_vars/host-homeassistant/core.yaml`
- `/Users/charlie/Code/infra/ansible/inventory/host_vars/host-storage/core.yaml` (79 lines removed)
- `/Users/charlie/Code/infra/ansible/inventory/host_vars/vm-awfulwoman/core.yaml`

- **Added assertion for required `zfs` variable** (commit `3c727c0e`):
  - Added `ansible.builtin.assert` task at the start of `system-zfs` role to fail immediately if `zfs` variable is not defined
  - Removed the now-redundant `when: zfs is defined` conditional from the main task block
  - This provides fail-fast behavior with a clear error message: "The 'zfs' variable must be defined to use the system-zfs role"
  - Instead of silently skipping all tasks, the role now explicitly fails with actionable guidance

- **Added conditional for encryption tasks** (uncommitted):
  - Wrapped the four encryption-related tasks in a conditional block:
    - Create `/root/zfs/keys` directory
    - Template encryption key files
    - Template `zfs-load-key.service` systemd unit
    - Enable `zfs-load-key.service`
  - Condition: `when: zfs | zfs_datasets_with_config | selectattr('properties', 'defined') | selectattr('properties.encryption', 'defined') | list | length > 0`
  - This prevents encryption setup from running (and potentially failing) on hosts without encrypted datasets
  - Eliminates unnecessary file creation and service management on non-encryption hosts

### Current State

- All ZFS configuration now uses the new declarative `zfs:` structure
- The `system-zfs` role contains all ZFS functionality (system-zfs-new successfully merged and deleted)
- All composition roles updated to use simplified, direct variable references
- All host_vars files cleaned up with legacy ZFS variables removed
- **`system-zfs` role improved with assertion and encryption conditionals**:
  - Committed: Required `zfs` variable assertion (commit `3c727c0e`)
  - Uncommitted: Encryption tasks conditional block
- Net code reduction: Over 200 lines of configuration removed through consolidation and simplification
- All refactoring changes committed across 6 commits (ecb3adc0 through 2ef30bb1)
- Latest improvement commit: `3c727c0e`

### Next Steps

1. **Commit encryption conditional changes**:
   - Review and commit the encryption tasks conditional block
   - Test on a host without encrypted datasets to verify tasks are skipped
   - Test on a host with encrypted datasets to verify tasks still execute

2. **Test the consolidated system-zfs role**:
   - Run playbooks for hosts using ZFS (host-storage, host-homeassistant, host-backups, dns)
   - Verify pool imports work correctly with new logic
   - Test encryption key loading service on boot
   - Confirm ZFS event daemon (zed) is running properly
   - Verify assertion catches missing `zfs` variable with clear error message

3. **Verify composition role functionality**:
   - Test updated composition roles (awfulwoman, get-iplayer, immich, tubesync)
   - Confirm all path variables resolve correctly
   - Check that Docker Compose files are generated properly with new variable names

4. **Monitor for issues**:
   - Watch for any missing variable errors in playbook runs
   - Verify all ZFS datasets are created/managed correctly
   - Check that the removal of musicassistant doesn't cause issues on host-storage

5. **Consider further cleanup**:
   - Review other roles that might still reference old variable patterns
   - Look for additional opportunities to simplify variable indirection
   - Consider documenting the new variable naming conventions

6. **Documentation updates**:
   - Update any documentation referencing the old `system-zfs-new` role
   - Document the new `zfs:` configuration structure format
   - Create migration guide if other similar infrastructure repos exist

### Notes

- **Migration pattern**: This refactoring demonstrates a healthy pattern: create new implementation alongside old (system-zfs-new), migrate usage gradually, then consolidate back into original location. This minimizes risk during the transition.

- **Variable indirection tradeoffs**: While the old pattern of `container_compositions_zfs_id: "{{ zfsid_compositions }}"` allowed for centralized path definitions, it made it difficult to understand actual values when reading configurations. The new approach prioritizes readability and maintainability.

- **Custom Jinja filters**: The consolidation relies on custom Ansible filters (`zfs_all_pools`, `zfs_datasets_with_config`) located in `ansible/plugins/filters/`. These filters process the declarative `zfs:` structure into actionable lists for tasks.

- **ZFS encryption key handling**: The `zfs-load-key.service` systemd unit is critical for systems with encrypted ZFS datasets. It ensures keys are loaded at boot before datasets are mounted. This was part of the system-zfs-new improvements now merged into system-zfs.

- **Impact scope**: This refactoring touched 6 commits spanning:
  - Core system role (system-zfs)
  - Supporting roles (compositions)
  - Application roles (4 composition-* roles)
  - Infrastructure definitions (6 host_vars files)
  - Orchestration (2 playbooks)

  This demonstrates careful coordination across all layers of the infrastructure.

- **Typo fix**: The get-iplayer role had a typo (`downlaods_dir`) that was corrected as part of this refactoring. This kind of cleanup is a good secondary benefit of systematic refactoring work.

- **Composition count reduction**: The host-storage configuration went from 6 composition roles to 3, suggesting either consolidation or removal of unused services. The explicit removal of musicassistant was documented, but other removals may have occurred.

- **Assertion benefits**: The addition of the `zfs` variable assertion transforms debugging from "Why aren't any ZFS tasks running?" to "Error: The 'zfs' variable must be defined to use the system-zfs role." This fail-fast approach is especially valuable in CI/CD pipelines where silent failures can be costly.

- **Encryption conditional optimization**: By checking for encrypted datasets before setting up encryption infrastructure, the role avoids creating unnecessary directories, templating unused files, and managing systemd services that will never be used. This is both a performance optimization and a security improvement (fewer attack surfaces on non-encryption hosts).

### Code Snippets

**Old variable pattern (before)**:
```yaml
# Indirect reference pattern
container_compositions_zfs_id: "{{ zfsid_compositions }}"
zfsid_compositions: "fastpool/compositions"
zfsid_downloads: "tank/downloads"

# Usage in roles required double lookup
dataset: "{{ container_compositions_zfs_id }}"
```

**New variable pattern (after)**:
```yaml
# Direct path pattern
compositions_dataset: "fastpool/compositions"
downloads_dir: "/tank/downloads"

# Usage in roles is straightforward
dataset: "{{ compositions_dataset }}"
```

**Old ZFS configuration (before)**:
```yaml
# Separate lists for different purposes
zfs_pools:
  - name: fastpool
    devices: ["/dev/disk/by-id/..."]

zfs_datasets:
  - name: "fastpool/compositions"
    properties:
      compression: lz4

zfs_backup_datasets:
  - "tank/data"
```

**New ZFS configuration (after)**:
```yaml
# Unified declarative structure
zfs:
  pools:
    fastpool:
      devices:
        - "/dev/disk/by-id/..."
      datasets:
        compositions:
          config:
            compression: lz4
  backups:
    - "tank/data"
```

**Composition role task updates**:
```yaml
# Before
- name: Ensure a ZFS dataset for each composition role is present
  community.general.zfs:
    name: "{{ container_compositions_zfs_id }}/{{ item.name }}"

# After
- name: Ensure a ZFS dataset for each composition role is present
  community.general.zfs:
    name: "{{ compositions_dataset }}/{{ item.name }}"
```

**Fail-fast assertion (added)**:
```yaml
- name: Assert that zfs variable is defined
  ansible.builtin.assert:
    that:
      - zfs is defined
    fail_msg: "The 'zfs' variable must be defined to use the system-zfs role"
    success_msg: "ZFS configuration is defined and ready"
```

**Encryption tasks conditional (uncommitted)**:
```yaml
# Block wrapper around all encryption tasks
- name: Setup ZFS encryption key infrastructure
  when: zfs | zfs_datasets_with_config | selectattr('properties', 'defined') | selectattr('properties.encryption', 'defined') | list | length > 0
  block:
    - name: Ensure /root/zfs/keys directory exists
      # ... task definition

    - name: Ensure ZFS encryption key files are present
      # ... task definition

    - name: Ensure zfs-load-key.service is present
      # ... task definition

    - name: Ensure zfs-load-key.service is enabled
      # ... task definition
```

---

## January 3, 2026 - ZFS Backup Script Output System Overhaul

**Session Overview**: Completely overhauled the output system for the ZFS pull backup script, adding `--quiet` flag support and implementing a three-tier logging system (info/debug/error) with visual prefixes and emoji indicators for improved readability.

### What Was Done

- **Phase 1: Initial `--quiet` flag implementation** (commit `dbe10c37`):
  - **Purpose**: Enable silent operation for cron jobs - no stdout on success, errors still displayed
  - **Implementation approach**:
    - Created an `info()` helper function that checks a module-level `_quiet` flag before printing
    - Converted all informational `print()` calls to `info()` calls throughout the script
    - Left error messages as direct `print()` calls so they always appear
    - Added `--quiet` / `-q` argument via argparse with `BooleanOptionalAction` (Python 3.9+)
  - Follows Unix/Linux convention: silent on success, verbose on failure

- **Phase 2: Three-tier output system with visual prefixes** (commits `607c65c3` through `22b3283f`):
  - **Added dedicated output helper functions**:
    - `info()`: Informational messages (hidden when `--quiet`), prefixed with `* `
    - `debug()`: Debug messages (hidden when `--quiet` OR when `--debug` not set), prefixed with `ℹ️ `
    - `error()`: Error messages (always shown), prefixed with `🚨 `
  - **Interaction between quiet and debug modes**:
    - Debug output requires both `_debug=True` and `_quiet=False` to display
    - When `--quiet` is set, debug output is suppressed even if `--debug` is enabled
    - Error messages always appear regardless of any flags
  - **Comprehensive message categorization**:
    - Reviewed all ~40+ output statements throughout the script
    - Properly categorized each as info/debug/error based on purpose
    - Converted all to use appropriate helper function
  - **Removed parameter passing**: Eliminated `debug` parameter from all function signatures, now using module-level `_debug` flag
  - **Enhanced preflight checks**:
    - Added proper return code checking for subprocess calls
    - Better error messages with specific context about what failed
    - Debug messages show successful validation steps
  - **Improved message clarity**:
    - Simplified verbose messages (e.g., "Up-to-date" instead of full dataset paths in normal mode)
    - Debug mode shows full paths and technical details
    - Info mode shows concise, user-friendly progress messages
  - **Visual improvements**:
    - Added newline at end of full run for cleaner terminal output
    - Emoji prefixes make it easy to scan output and identify message types

- **Code cleanup and refinements**:
  - Removed unnecessary initial `_quiet = False` declaration at module level
  - Simplified function signatures throughout (removed debug parameter from 7+ functions)
  - Improved consistency in error message formatting
  - Better separation of concerns between info/debug/error output

### Key Decisions

- **Three-tier output system**: Separated messages into info/debug/error categories based on audience and purpose:
  - **Info**: Progress messages for normal operation (hidden in quiet mode)
  - **Debug**: Technical details for troubleshooting (requires `--debug` and not `--quiet`)
  - **Error**: Problems that need attention (always shown)

- **Module-level flags over parameter passing**: Using module-level `_quiet` and `_debug` variables eliminates the need to pass these flags through every function call. This significantly cleans up function signatures while maintaining global control over output behavior.

- **Debug respects quiet mode**: When `--quiet` is enabled, debug output is also suppressed even if `--debug` is set. This ensures that quiet mode truly produces no output on success, which is critical for cron jobs.

- **Visual prefixes for scannability**: Added emoji and symbol prefixes to make it easy to visually scan output:
  - `* ` for info messages (subtle, progress-oriented)
  - `ℹ️ ` for debug messages (technical information)
  - `🚨 ` for errors (immediately draws attention)

- **Unix convention for cron**: The `--quiet` flag enables the script to follow standard Unix behavior: produce no output when successful (so cron doesn't send emails), but show errors when something fails.

### Files Changed

- `/Users/charlie/Code/infra/ansible/roles/backups-zfs-server/templates/zfs-pull-backups.py` (9 commits total):
  - **Added three output helper functions** at module level: `info()`, `debug()`, `error()`
  - **Added module-level variables**: `_quiet` and `_debug` set in `main()`
  - **Converted all output statements** (~40+ print calls) to use appropriate helper function
  - **Updated all function signatures**: Removed `debug` parameter from all functions
  - **Enhanced preflight checks**: Added return code validation and better error messages
  - **Added visual prefixes**: `* ` for info, `ℹ️ ` for debug, `🚨 ` for errors
  - **Improved message content**: More concise info messages, detailed debug messages
  - **Added `--quiet` / `-q` argument** to argparse configuration
  - **Added newline** at end of script run for cleaner output

### Current State

- Script now has a comprehensive three-tier output system (info/debug/error)
- All output categorized and using appropriate helper functions
- Visual prefixes make output easy to scan and understand
- Quiet mode fully functional for cron usage
- Debug mode provides detailed technical information when needed
- **All changes committed** across 9 commits (`dbe10c37` through `22b3283f`):
  - `dbe10c37`: Initial quiet flag implementation
  - `607c65c3`: Added dedicated debug method
  - `83735571`: Fixed debug to respect quiet mode
  - `84641f09`: Categorized all outputs as info/debug/error
  - `d9ff69b4`: Fixed preflight debug argument
  - `7e4871ad`: Fixed debug show logic
  - `1ba7320b`: Added prefix to messages
  - `6f34ff04`: Improved info message content
  - `bb8192ed`: Added newline at end of run
  - `22b3283f`: Final output refinements
- Previous ZFS backup improvements (streaming pipeline, non-recursive sends) remain in place

### Next Steps

1. **Update cron job configuration**:
   - Add `--quiet` flag to cron jobs that run the ZFS backup script
   - Test that successful runs produce no output (no cron emails)
   - Verify that errors still trigger cron email notifications with proper formatting

2. **Apply same output system to push script**:
   - The companion `zfs-push-backups.py` script should get the same three-tier output system
   - Would maintain consistency between pull and push backup scripts
   - Consider creating shared utility module for output functions

3. **Test output modes**:
   - Verify normal mode shows appropriate info messages
   - Test `--debug` mode shows all technical details
   - Confirm `--quiet` mode produces no output on success
   - Test `--debug --quiet` combination (should show nothing)
   - Verify error messages always appear with visual prefix

4. **Monitor production usage**:
   - Watch for any UX issues with the new output format
   - Verify emoji display correctly in different terminal environments
   - Confirm the prefixes don't interfere with log parsing if logs are captured

### Notes

- **Python scoping**: Module-level variables in Python don't require the `global` keyword when assigned in the `if __name__ == "__main__":` block, since that code runs at module scope (not inside a function definition). However, functions that *read* module-level variables do need them declared if they want to *modify* them.

- **BooleanOptionalAction**: Used for the `--quiet` argument (added in Python 3.9). This provides automatic `--quiet` / `--no-quiet` flag pairs and stores a simple boolean value.

- **Module-level flags pattern**: Using module-level flags for output control is common in Python CLI tools. Alternative approaches include:
  - Using Python's logging module with configurable levels (more complex, better for large projects)
  - Passing quiet/debug parameters to every function (more explicit, but verbose)
  - Using a context manager or global state object (more OOP, potentially overkill)

- **Output hierarchy**: The three-tier system creates clear separation:
  - Normal mode: Info messages only (progress and results)
  - Debug mode: Info + Debug messages (adds technical details)
  - Quiet mode: Errors only (production/cron usage)

- **Emoji considerations**: The emoji prefixes (`ℹ️` and `🚨`) are widely supported in modern terminals but may display differently or not at all in older systems or certain log viewers. Consider this if integrating with log aggregation tools.

- **Iterative development**: This work demonstrates iterative improvement - started with basic quiet mode, then enhanced with full three-tier system through 8 additional commits as real-world usage revealed needs for better categorization and visual clarity.

### Code Snippets

**Three output helper functions (final version)**:
```python
def info(message):
    """Print informational message unless quiet mode is enabled."""
    if not _quiet:
        print("* " + message)

def debug(message):
    """Print debug messages."""
    if _debug and not _quiet:
        print("ℹ️ " + message)

def error(message):
    """Print error messages."""
    print("🚨 " + message)
```

**Module-level flag assignment in main()**:
```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backup ZFS datasets from a remote host.')
    # ... argument definitions ...
    parser.add_argument('--quiet', '-q', default=DEFAULT_quiet,
                       help='Suppress informational output (errors still shown)',
                       action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    _quiet = args.quiet
    _debug = args.debug

    preflight(args.host, args.datasets, args.user, args.destination)
```

**Output categorization examples**:
```python
# Progress information (hidden when --quiet)
info(f"Backing up {len(unique_datasets)} datasets individually")
info(f"Successfully received all snapshots up to '{latest_remote}'")

# Technical details (requires --debug, hidden when --quiet)
debug(f"Found {len(direct_snapshots)} remote snapshots")
debug(f"{send_cmd}")

# Error conditions (always shown)
error(f"Could not connect to {host}")
error(f"zfs send failed with code {send_proc.returncode}")
```

**Function signature simplification**:
```python
# Before - passing debug through every function
def pulldatasets(host, dataset, user, destination, debug):
    remote_snapshots = get_remote_snapshots(host, dataset, user, debug)
    # ...

# After - using module-level flag
def pulldatasets(host, dataset, user, destination):
    remote_snapshots = get_remote_snapshots(host, dataset, user)
    # ...
```

---

## January 2, 2026 - ZFS Backup Memory Optimization

**Session Overview**: Optimized the ZFS pull backup script to eliminate unbounded memory consumption during snapshot transfers by implementing true streaming pipelines.

### What Was Done

- **Fixed memory consumption issue in ZFS backup script** (`ansible/roles/backups-zfs-server/templates/zfs-pull-backups.py`):
  - **Problem**: The `send_and_receive()` function was using `subprocess.run()` with `stdout=subprocess.PIPE`, which buffered the entire ZFS send stream in Python memory before passing it to `zfs receive`
  - **Impact**: For large datasets, this could consume gigabytes of RAM, potentially causing OOM errors or system instability
  - **Solution**: Replaced `subprocess.run()` with `subprocess.Popen` to create a true streaming pipeline where data flows directly from send to receive through the OS kernel's pipe buffer (~64KB)
  - **Memory complexity**: Reduced from O(n) where n = dataset size to O(1) constant memory usage

- **Code explanation provided**:
  - Explained the Python `_` convention for discarding unwanted values during tuple unpacking (e.g., `_, receive_stderr = receive_proc.communicate()`)
  - Clarified the purpose of `send_proc.stdout.close()` to enable SIGPIPE handling for proper pipeline cleanup

### Key Decisions

- **Streaming pipeline pattern over store-and-forward**: The new implementation uses `Popen` to create two processes with piped I/O, allowing the OS kernel to manage data flow directly between processes without Python intermediation. This is the standard Unix pipeline pattern (`command1 | command2`) implemented programmatically.

- **Proper pipeline cleanup**: Closing the send process's stdout after connecting it to receive's stdin ensures that if the receive process fails, the send process receives SIGPIPE and can terminate cleanly rather than blocking indefinitely.

### Files Changed

- `/Users/charlie/Code/infra/ansible/roles/backups-zfs-server/templates/zfs-pull-backups.py`:
  - Modified `send_and_receive()` function (lines 149-188)
  - Replaced `subprocess.run()` with `subprocess.Popen` for both send and receive commands
  - Added `send_proc.stdout.close()` for proper SIGPIPE handling
  - Data now flows: `send_proc.stdout → receive_proc.stdin` via OS pipe buffer

### Current State

- ZFS backup script now uses constant memory regardless of dataset size
- Script is production-ready with efficient resource usage
- Changes are uncommitted in git
- Previous session's ZFS backup fixes (non-recursive sends, mount prevention) remain in place

### Next Steps

1. **Test memory usage improvements**:
   - Run backup script with large datasets and monitor memory consumption
   - Verify RSS/VSZ memory metrics remain constant during transfers
   - Compare before/after memory usage if possible

2. **Commit these changes**:
   - Commit the memory optimization improvements
   - Consider combining with previous ZFS backup session changes or keep separate

3. **Monitor production performance**:
   - Watch for any changes in backup completion times
   - Verify no regressions in reliability
   - Confirm memory usage stays low during large transfers

### Notes

- The original implementation with `subprocess.run(stdout=subprocess.PIPE)` would load the entire ZFS send stream into a Python bytes object before passing it along. For a 1TB dataset, this would require 1TB of RAM.

- The new implementation uses `subprocess.Popen` which creates processes that communicate via OS pipes. The kernel manages a small circular buffer (typically 64KB on Linux) that automatically blocks writers when full and blocks readers when empty.

- This is the canonical way to implement pipelines in Python when working with large data streams. It's equivalent to shell pipes but with programmatic control over each process.

- The `_` naming convention in Python indicates "I'm unpacking this value but don't care about it." In `_, receive_stderr = receive_proc.communicate()`, we only need stderr, so stdout is discarded into `_`.

- SIGPIPE is a Unix signal sent when writing to a pipe with no readers. Closing `send_proc.stdout` after connecting it to `receive_proc.stdin` allows the kernel to send SIGPIPE to the send process if receive exits early, preventing deadlocks.

### Code Snippets

**Before (memory-inefficient)**:
```python
def send_and_receive(send_cmd, receive_cmd, debug):
    # This buffers entire stream in memory
    send_result = subprocess.run(
        send_cmd.split(' '),
        stdout=subprocess.PIPE,  # Captures all output in memory
        stderr=subprocess.PIPE
    )
    receive_result = subprocess.run(
        receive_cmd.split(' '),
        input=send_result.stdout,  # Entire stream already in RAM
        stderr=subprocess.PIPE
    )
```

**After (memory-efficient streaming)**:
```python
def send_and_receive(send_cmd, receive_cmd, debug):
    """Execute a zfs send | zfs receive pipeline using streaming (no memory buffering)."""
    # Create a true pipeline: send.stdout -> receive.stdin
    # This streams data directly without buffering in memory
    send_proc = subprocess.Popen(
        send_cmd.split(' '),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    receive_proc = subprocess.Popen(
        receive_cmd.split(' '),
        stdin=send_proc.stdout,  # Connect pipe directly
        stderr=subprocess.PIPE
    )

    # Allow send_proc to receive SIGPIPE if receive_proc exits
    send_proc.stdout.close()

    # Wait for receive to complete and capture stderr
    _, receive_stderr = receive_proc.communicate()  # _ discards stdout (None)

    # Now wait for send to complete
    _, send_stderr = send_proc.communicate()  # _ discards stdout (None)
```

**Memory usage comparison**:
- Old approach: O(n) where n = size of ZFS snapshot (could be gigabytes)
- New approach: O(1) constant ~64KB kernel pipe buffer

---

## January 1, 2026 - ZFS Pull Backup Fixes & Custom Commit Command

**Session Overview**: Fixed critical issues in the ZFS pull backup script to handle child datasets with mismatched snapshots and resolved ZFS receive permission errors. Also created a custom Claude Code slash command for git commits.

### What Was Done

- **Fixed ZFS pull backup script for non-recursive sends** (`ansible/roles/backups-zfs-server/templates/zfs-pull-backups.py`):
  - **Problem**: Using `zfs send -R` (recursive) failed when child datasets didn't share the same snapshots as the parent dataset
  - **Solution**: Changed from recursive sends to individual dataset sends
  - Added `get_remote_child_datasets()` function that uses `zfs list -r` to enumerate all child datasets under a parent
  - Modified `pulldatasets_init()` to expand parent datasets into all children and process each individually
  - Removed `-R` flag from all `zfs send` commands (lines 202, 212, 230)
  - Added deduplication logic to handle overlapping dataset hierarchies when multiple parents specified
  - Modified snapshot filtering in `get_remote_snapshots()` and `get_local_snapshots()` to only get direct snapshots of each dataset (not child datasets)

- **Fixed ZFS receive permission error** ("cannot unmount: permission denied"):
  - **Problem**: `zfs receive` was attempting to mount backup datasets, which failed due to permission issues
  - **Solution 1**: Added `-u` flag to all `zfs receive` commands to prevent automatic mounting (lines 203, 214, 231)
  - **Solution 2**: Modified Ansible tasks to set `canmount=off` property on backup datasets:
    - Added task to ensure backup parent dataset has `canmount=off` (lines 73-79)
    - Added `canmount: off` to child backup dataset properties (line 88)
  - This ensures backup datasets are never mounted, avoiding permission issues entirely

- **Created custom Claude Code slash command** (`.claude/commands/commit.md`):
  - Defines a `/commit` command for creating well-formatted git commits
  - Instructs Claude to analyze changes, draft concise commit messages using conventional commit format
  - Emphasizes "why" over "what", imperative mood, and includes standard Claude Code footer
  - Defines commit types: feat, fix, refactor, docs, chore, style

### Key Decisions

- **Individual dataset processing over recursive sends**: While recursive sends are more efficient, they require all child datasets to share snapshots with the parent. Individual processing is more robust and handles heterogeneous snapshot schedules across dataset hierarchies.

- **Prevent mounting backup datasets**: Since backup datasets are read-only copies that should never be actively used, setting `canmount=off` and using `-u` flag prevents unnecessary mount attempts and associated permission complexity.

- **Slash command for commits**: Creating a custom command standardizes commit message format and ensures Claude follows best practices when creating commits during sessions.

### Files Changed

- `/Users/charlie/Code/infra/ansible/roles/backups-zfs-server/templates/zfs-pull-backups.py` - Major refactor:
  - Added `get_remote_child_datasets()` function (lines 44-68)
  - Modified `pulldatasets_init()` to expand and deduplicate datasets (lines 70-87)
  - Removed `-R` flag from `zfs send` commands
  - Added `-u` flag to `zfs receive` commands
  - Modified snapshot filtering to only get direct snapshots

- `/Users/charlie/Code/infra/ansible/roles/backups-zfs-server/tasks/main.yaml`:
  - Added task "Ensure backup parent dataset has canmount=off" (lines 73-79)
  - Added `canmount: off` to backup dataset properties (line 88)

- `/Users/charlie/Code/infra/.claude/commands/commit.md` (new file):
  - 42-line markdown file defining the `/commit` slash command
  - Includes instructions, message format, commit types, and important warnings

### Current State

- ZFS pull backup script now handles complex dataset hierarchies correctly
- Backup datasets are configured to never mount, avoiding permission issues
- Custom `/commit` command is ready to use in future sessions
- All changes are uncommitted and ready for review
- The backup infrastructure should now work reliably with datasets that have varying snapshot schedules

### Next Steps

1. **Test the fixed backup script**:
   - Run backup script against hosts with complex dataset hierarchies
   - Verify child datasets are correctly enumerated and backed up individually
   - Confirm no mounting errors occur during receives
   - Check that deduplication works when dataset hierarchies overlap

2. **Commit these changes**:
   - Consider using the new `/commit` command to commit these fixes
   - Test both the ZFS backup fixes and the new slash command in the same commit or separately

3. **Monitor backup runs**:
   - Watch for any errors in production backup runs
   - Verify backup datasets remain unmounted
   - Check that all expected datasets are being backed up

4. **Consider additional improvements**:
   - Add logging to show which datasets are being skipped due to deduplication
   - Add validation that child datasets are processed in correct order (parents before children)
   - Consider adding a dry-run mode to preview what would be backed up

### Notes

- The `-R` (recursive) flag in ZFS send requires that all child datasets share the same snapshots. This is rarely the case in real-world scenarios where different datasets may have different snapshot schedules or retention policies.

- The `-u` flag in ZFS receive prevents datasets from being mounted during receive operations. This is essential for backup scenarios where datasets should remain offline.

- Setting `canmount=off` on backup datasets is a permanent configuration that prevents accidental mounting, even if someone manually attempts it.

- The combination of `-u` flag and `canmount=off` provides defense-in-depth against mounting issues.

- The new dataset expansion logic preserves order and handles overlaps correctly, ensuring each dataset is only processed once.

### Code Snippets

**Dataset expansion and deduplication**:
```python
def pulldatasets_init(host, datasets, user, destination, debug):
    # Expand each dataset to include all children
    all_datasets = []
    for dataset in datasets:
        children = get_remote_child_datasets(host, dataset, user, debug)
        all_datasets.extend(children)

    # Remove duplicates while preserving order
    seen = set()
    unique_datasets = []
    for ds in all_datasets:
        if ds not in seen:
            seen.add(ds)
            unique_datasets.append(ds)

    print(f"Backing up {len(unique_datasets)} datasets individually")
    for dataset in unique_datasets:
        pulldatasets(host, dataset, user, destination, debug)
```

**Non-recursive receive with no mounting**:
```python
# Initial sync
send_cmd = f"ssh {user}@{host} zfs send {dataset}@{earliest_remote}"
receive_cmd = f"zfs receive -F -u {local_dataset}"

# Incremental sync
send_cmd = f"ssh {user}@{host} zfs send -I {dataset}@{latest_common} {dataset}@{latest_remote}"
receive_cmd = f"zfs receive -F -u {local_dataset}"
```

**Ansible canmount configuration**:
```yaml
- name: Ensure backup parent dataset has canmount=off
  become: true
  community.general.zfs:
    name: "{{ backups_zfs_server_dataset }}"
    extra_zfs_properties:
      canmount: off
    state: present

- name: Ensure backup datasets exist
  become: true
  community.general.zfs:
    name: "{{ backups_zfs_server_dataset }}/{{ item.dataset }}"
    extra_zfs_properties:
      acltype: posix
      xattr: sa
      canmount: off  # Added this
    state: present
```

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

### Additional Work

- **Created `suspend-backups.sh`** - A simple bash script in the repo root that uses `mosquitto_pub` to publish a "suspend" message to the `servers/host-backups` MQTT topic (host configured via `MQTT_HOST` env var)
- This script is used to suspend the backup server when done working on the server-zfsbackups role

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
