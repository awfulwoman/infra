#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse
from datetime import datetime, timedelta
import json
import re
import os
import atexit
import signal

DEFAULT_destination = "{{ backups_zfs_server_local_dataset }}"
DEFAULT_user="{{ vault_zfsbackups_user }}"
DEFAULT_debug = False
DEFAULT_quiet = False
STALE_LOCK_HOURS = {{ backups_zfs_server_stale_lock_hours }}
HOLD_ENABLED = {{ backups_zfs_server_hold_enabled | bool }}
HOLD_TAG = "{{ backups_zfs_server_hold_tag }}"

# Lockfile to prevent concurrent executions (set dynamically per host)
_lockfile = None

# Module-level variables for output control (set by main)
_quiet = False
_debug = False


def get_lockfile_path(host):
    """Generate a host-specific lockfile path.

    Sanitizes the hostname to create a safe filesystem path.
    This allows parallel pulls from different hosts.
    """
    # Sanitize hostname: replace non-alphanumeric chars with hyphens
    safe_host = re.sub(r'[^a-zA-Z0-9.-]', '-', host)
    return f"/var/run/zfs-pull-backups-{safe_host}.lock"

def info(message):
    """Print informational message unless quiet mode is enabled."""
    if not _quiet:
        print("* " + message)

def debug(message):
    """Print debug messages."""
    if _debug and not _quiet:
        print("ℹ️ " + message)

def error(message):
    """Print error messages to stderr."""
    print("🚨 " + message, file=sys.stderr)


def acquire_lock():
    """Acquire lockfile to prevent concurrent executions.

    Uses PID-based locking to detect and clean up stale locks.
    Returns True if lock acquired successfully, False otherwise.
    """
    if os.path.exists(_lockfile):
        # Lockfile exists - check if it's stale
        try:
            with open(_lockfile, 'r') as f:
                old_pid = int(f.read().strip())

            # Check if process with that PID is still running
            try:
                os.kill(old_pid, 0)  # Signal 0 just checks if process exists
                # Process exists - lock is valid
                error(f"Another instance is already running (PID {old_pid})")
                error("If you believe this is an error, remove the lockfile: " + _lockfile)
                return False
            except (OSError, ProcessLookupError):
                # Process doesn't exist - stale lockfile
                debug(f"Removing stale lockfile (PID {old_pid} not running)")
                os.remove(_lockfile)
        except (ValueError, IOError) as e:
            # Corrupted lockfile - remove it
            debug(f"Removing corrupted lockfile: {e}")
            try:
                os.remove(_lockfile)
            except OSError:
                pass

    # Create lockfile with current PID
    try:
        with open(_lockfile, 'w') as f:
            f.write(str(os.getpid()))
        debug(f"Acquired lock for {_lockfile} (PID {os.getpid()})")
        return True
    except IOError as e:
        error(f"Failed to create lockfile: {e}")
        return False


def lockfile_age_hours():
    """How long the current lockfile has been held, or None if it is gone."""
    try:
        held_since = datetime.fromtimestamp(os.path.getmtime(_lockfile))
    except OSError:
        return None
    return (datetime.now() - held_since).total_seconds() / 3600


def release_lock():
    """Release the lockfile."""
    try:
        if os.path.exists(_lockfile):
            # Verify it's our lockfile before removing
            with open(_lockfile, 'r') as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(_lockfile)
                debug(f"Released lock for {_lockfile} (PID {os.getpid()})")
            else:
                debug(f"Not removing lockfile - belongs to PID {pid}, not {os.getpid()}")
    except (ValueError, IOError, OSError) as e:
        debug(f"Error releasing lock: {e}")


def signal_handler(signum, frame):
    """Handle termination signals by cleaning up lockfile."""
    signal_names = {
        signal.SIGTERM: 'SIGTERM',
        signal.SIGINT: 'SIGINT',
        signal.SIGHUP: 'SIGHUP'
    }
    debug(f"Received {signal_names.get(signum, signum)}, cleaning up...")
    release_lock()
    sys.exit(1)


def preflight(host, name, datasets, user, destination):
    info('Checking remote host is up')
    result = subprocess.run(['ssh', f'{user}@{host}', 'ls'],
            shell=False,
            check=False,
            capture_output=True
            )
    if result.returncode != 0:
        error(f'Could not connect to {host}\n  ssh: {result.stderr.decode().strip()}')
        sys.exit(1)
    info(f'{host} is up')

    for dataset in datasets:
        debug(f'Checking remote source {dataset} exists')
        result = subprocess.run(
            ['ssh', f'{user}@{host}', f'zfs list {dataset}'],
            shell=False,
            check=False,
            capture_output=True
            )
        if result.returncode != 0:
            error(f'Remote dataset {dataset} does not exist\n  zfs: {result.stderr.decode().strip()}')
            sys.exit(1)
        debug(f'{dataset} exists')

    debug(f'Checking local destination {destination} exists')
    result = subprocess.run(['zfs', 'list', f'{destination}'],
            shell=False,
            check=False,
            capture_output=True
            )
    if result.returncode != 0:
        error(f'Local destination {destination} does not exist\n  zfs: {result.stderr.decode().strip()}')
        sys.exit(1)
    debug(f'Destination {destination} exists')

    pulldatasets_init(host, name, datasets, user, destination)

def get_remote_child_datasets(host, dataset, user):
    """Get all datasets under a parent (including the parent itself)."""
    command = f"ssh {user}@{host} zfs list -H -o name -r {dataset}"

    debug(command)

    try:
        result = subprocess.run(
            command.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        datasets = result.stdout.decode().strip().splitlines()

        debug(f"Found {len(datasets)} datasets under {dataset}")

        return datasets

    except subprocess.CalledProcessError as e:
        error(f"Could not list remote datasets:\n{e.stderr.decode()}")
        sys.exit(1)


def pulldatasets_init(host, name, datasets, user, destination):
    # Expand each dataset to include all children
    all_datasets = []
    for dataset in datasets:
        children = get_remote_child_datasets(host, dataset, user)
        all_datasets.extend(children)

    # Remove duplicates while preserving order
    seen = set()
    unique_datasets = []
    for ds in all_datasets:
        if ds not in seen:
            seen.add(ds)
            unique_datasets.append(ds)

    info(f"Datasets in queue: {len(unique_datasets)}")
    for dataset in unique_datasets:
        info(f'{host}:{dataset}')
        pulldatasets(host, name, dataset, user, destination)

def get_remote_snapshots(host, dataset, user):
    """Get all snapshot names for a dataset on remote host, sorted by creation time."""
    command = f"ssh {user}@{host} zfs list -t snapshot -H -o name -s creation -r {dataset}"

    debug(command)

    try:
        result = subprocess.run(
            command.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        snapshots = result.stdout.decode().strip().splitlines()
        # Filter to only direct snapshots of this dataset (not child datasets)
        direct_snapshots = [s.split("@")[1] for s in snapshots if s.startswith(f"{dataset}@")]

        debug(f"Found {len(direct_snapshots)} remote snapshots")

        return direct_snapshots

    except subprocess.CalledProcessError as e:
        error(f"Could not list remote snapshots:\n{e.stderr.decode()}")
        sys.exit(1)


def get_local_snapshots(dataset):
    """Get all snapshot names for a local dataset, sorted by creation time."""
    command = f"zfs list -t snapshot -H -o name -s creation -r {dataset}"

    debug(command)

    try:
        result = subprocess.run(
            command.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False  # Don't fail if dataset doesn't exist
        )
        if result.returncode != 0:
            return []  # Dataset doesn't exist yet

        snapshots = result.stdout.decode().strip().splitlines()
        # Filter to only direct snapshots of this dataset (not child datasets)
        direct_snapshots = [s.split("@")[1] for s in snapshots if s.startswith(f"{dataset}@")]

        debug(f"Found {len(direct_snapshots)} local snapshots")

        return direct_snapshots

    except Exception as e:
        error(f"Could not get local snapshots: {e}")
        return []


def send_and_receive(send_cmd, receive_cmd):
    """Execute a zfs send | zfs receive pipeline using streaming (no memory buffering)."""
    try:
        debug(f"{send_cmd}")
        debug(f"{receive_cmd}")

        # Create a true pipeline: send.stdout -> receive.stdin
        # This streams data directly without buffering in memory
        send_proc = subprocess.Popen(
            send_cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        receive_proc = subprocess.Popen(
            receive_cmd.split(' '),
            stdin=send_proc.stdout,
            stderr=subprocess.PIPE
        )

        # Allow send_proc to receive SIGPIPE if receive_proc exits
        send_proc.stdout.close()

        # Wait for receive to complete and capture stderr
        _, receive_stderr = receive_proc.communicate()

        # Now wait for send to complete
        _, send_stderr = send_proc.communicate()

        # Check if any part of the pipeline failed
        send_failed = send_proc.returncode != 0
        receive_failed = receive_proc.returncode != 0

        if send_failed or receive_failed:
            # Report which component(s) failed
            if send_failed:
                error(f"zfs send failed with code {send_proc.returncode}")
            if receive_failed:
                error(f"zfs receive failed with code {receive_proc.returncode}")

            # Report all captured stderr (the real error is often in receive)
            if send_stderr and send_stderr.strip():
                error(f"  send stderr: {send_stderr.decode().strip()}")
            if receive_stderr and receive_stderr.strip():
                error(f"  receive stderr: {receive_stderr.decode().strip()}")

            # If send failed but had no stderr, hint that the error is likely elsewhere
            if send_failed and not (send_stderr and send_stderr.strip()):
                if receive_stderr and receive_stderr.strip():
                    error("  (send likely failed due to broken pipe from receive failure)")
                else:
                    error("  (no stderr captured - try running with --debug for more info)")

            return False

        return True

    except Exception as e:
        error(f"Transfer failed: {e}")
        return False


def ensure_parent_datasets_exist(dataset_path):
    """Create all parent datasets if they don't exist.

    For example, if dataset_path is "pool/backups/raw/host/pool/dataset",
    this ensures that all parents exist:
      - pool/backups
      - pool/backups/raw
      - pool/backups/raw/host
      - pool/backups/raw/host/pool
    """
    parts = dataset_path.split('/')

    # Build list of all parent paths (excluding the leaf dataset itself)
    parents = []
    for i in range(1, len(parts)):
        parent = '/'.join(parts[:i])
        parents.append(parent)

    # Check and create each parent in order
    for parent in parents:
        # Check if dataset exists
        result = subprocess.run(
            ['zfs', 'list', '-H', '-o', 'name', parent],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )

        if result.returncode != 0:
            # Dataset doesn't exist, create it
            debug(f"Creating missing parent dataset: {parent}")

            create_result = subprocess.run(
                ['zfs', 'create', '-o', 'canmount=off', '-o', 'acltype=posix', '-o', 'xattr=sa', parent],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )

            if create_result.returncode != 0:
                error(f"Failed to create parent dataset {parent}")
                error(f"  zfs create: {create_result.stderr.decode().strip()}")
                sys.exit(1)

            info(f"Created parent dataset: {parent}")


def remote_run(host, user, args):
    """Run one command on the client over SSH. Returns (rc, stdout, stderr)."""
    result = subprocess.run(
        ['ssh', f'{user}@{host}'] + args,
        capture_output=True, check=False
    )
    return (result.returncode,
            result.stdout.decode().strip(),
            result.stderr.decode().strip())


def snapshots_we_hold(host, user, dataset):
    """Snapshots of `dataset` on the client that carry our hold tag."""
    # userrefs narrows to the handful of snapshots carrying any hold at all,
    # so we ask for tags on those rather than on the thousands a critical
    # dataset accumulates.
    rc, out, _ = remote_run(host, user, [
        'zfs', 'get', '-H', '-o', 'name,value', '-t', 'snapshot',
        '-d', '1', 'userrefs', dataset,
    ])
    if rc != 0 or not out:
        return []

    candidates = [
        line.split('\t')[0] for line in out.splitlines()
        if line.split('\t')[-1] not in ('0', '-')
    ]
    if not candidates:
        return []

    rc, out, _ = remote_run(host, user, ['zfs', 'holds', '-H'] + candidates)
    if rc != 0 or not out:
        return []

    held = []
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) >= 2 and parts[1] == HOLD_TAG:
            held.append(parts[0])
    return held


def update_hold(host, user, dataset, keep):
    """Pin the snapshot the replica now sits on; let the previous one go.

    Retention on the client prunes by age and knows nothing about what this
    backup server still needs. Once the last snapshot the two share is gone,
    no incremental send is possible and the only route back is destroying the
    replica and sending the whole dataset again. That is how fifteen datasets
    here stopped replicating between May and July 2026, silently, one outage
    at a time.

    A hold makes that snapshot undestroyable, so the common base survives
    however long the backup server is away.
    """
    if not HOLD_ENABLED:
        return

    target = f"{dataset}@{keep}"
    held = snapshots_we_hold(host, user, dataset)

    if target not in held:
        rc, _, err = remote_run(host, user, ['zfs', 'hold', HOLD_TAG, target])
        if rc != 0 and 'already exists' not in err:
            # Worth saying, but not worth failing the pull: the data arrived,
            # and the next run will try the hold again.
            error(f"Could not hold {target}: {err}")
            return
        debug(f"Held {target} as {HOLD_TAG}")

    # Exactly one snapshot per dataset stays held. Leave the old bases pinned
    # and the client keeps every snapshot it ever sent us, filling its pool.
    for snapshot in held:
        if snapshot == target:
            continue
        rc, _, err = remote_run(host, user, ['zfs', 'release', HOLD_TAG, snapshot])
        if rc != 0:
            error(f"Could not release {snapshot}: {err}")
        else:
            debug(f"Released hold on {snapshot}")


def pulldatasets(host, name, dataset, user, destination):
    local_dataset = f"{destination}/{name}/{dataset}"

    remote_snapshots = get_remote_snapshots(host, dataset, user)
    if not remote_snapshots:
        info(f"Skipping {dataset} - no snapshots found on remote")
        return

    local_snapshots = get_local_snapshots(local_dataset)

    earliest_remote = remote_snapshots[0]
    latest_remote = remote_snapshots[-1]

    # Find common snapshots between local and remote
    common_snapshots = [s for s in local_snapshots if s in remote_snapshots]

    if not common_snapshots:
        # Initial sync: no common snapshots, need full send
        info(f"No common snapshots found.")
        info(f"Remote has {len(remote_snapshots)} snapshots: {earliest_remote} -> {latest_remote}")
        info(f"Performing initial sync.")

        # Ensure all parent datasets exist before receiving
        ensure_parent_datasets_exist(local_dataset)

        # Step 1: Full send of earliest snapshot
        # Don't use -F for initial receive - let dataset be created with inherited properties
        info(f"{dataset} is new. Pulling the earliest snapshot: '@{earliest_remote}'")
        send_cmd = f"ssh {user}@{host} zfs send {dataset}@{earliest_remote}"
        receive_cmd = f"zfs receive -u {local_dataset}"

        if not send_and_receive(send_cmd, receive_cmd):
            sys.exit(1)
        info(f"Success! Received earliest snapshot.")
        debug(f"{dataset}@{earliest_remote}")

        # Step 2: Incremental from earliest to latest (if more than one snapshot)
        if earliest_remote != latest_remote:
            info(f"Pulling incremental snapshots between '{earliest_remote}' and '{latest_remote}'")
            send_cmd = f"ssh {user}@{host} zfs send -I {dataset}@{earliest_remote} {dataset}@{latest_remote}"
            # Only use -F for incrementals once dataset exists
            receive_cmd_incremental = f"zfs receive -F -u {local_dataset}"

            if not send_and_receive(send_cmd, receive_cmd_incremental):
                sys.exit(1)
            info(f"Success! Latest snapshot is '{latest_remote}'")
            update_hold(host, user, dataset, latest_remote)
        else:
            info("Only one snapshot exists, no incremental receive needed.")
            update_hold(host, user, dataset, earliest_remote)

    else:
        # Incremental sync: find latest common snapshot and sync from there
        latest_common = common_snapshots[-1]

        if latest_common == latest_remote:
            info(f"Up-to-date!")
            debug(f"Latest is {dataset}@{latest_remote}")
            # Nothing to transfer, but the hold still has to move forward, or
            # a dataset that rarely changes keeps its base pinned at an
            # ever-older snapshot and eventually loses it anyway.
            update_hold(host, user, dataset, latest_remote)
            return

        info(f"Partially synced.")
        info(f"Updating from {latest_common}' to '{latest_remote}'.")
        send_cmd = f"ssh {user}@{host} zfs send -I {dataset}@{latest_common} {dataset}@{latest_remote}"
        receive_cmd = f"zfs receive -F -u {local_dataset}"

        if not send_and_receive(send_cmd, receive_cmd):
            sys.exit(1)
        info(f"Success. Latest snapshot is now '{latest_remote}'.")
        update_hold(host, user, dataset, latest_remote)

    print('\n')

def get_newest_autosnap_time(dataset):
    """Return the datetime of the newest autosnap snapshot for a local dataset, or None."""
    snapshots = get_local_snapshots(dataset)
    autosnap_snaps = [s for s in snapshots if s.startswith('autosnap_')]
    if not autosnap_snaps:
        return None
    newest = autosnap_snaps[-1]
    match = re.match(r'^autosnap_(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})_', newest)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d_%H:%M:%S")
    return None


def publish_mqtt_discovery(name, mqtt_host, mqtt_topic_prefix):
    """Publish HA MQTT discovery config for the pull binary sensor."""
    safe_id = name.replace('-', '_').replace('.', '_')
    state_topic = f"{mqtt_topic_prefix}/{name}/backups"
    discovery_topic = f"homeassistant/binary_sensor/zfs_backups_{safe_id}/config"
    payload = json.dumps({
        "name": f"{name} ZFS Backups",
        "state_topic": state_topic,
        "value_template": "{{ '{{' }} 'ON' if not value_json.ok else 'OFF' {{ '}}' }}",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device_class": "safety",
        "unique_id": f"zfs_backups_{safe_id}",
        "json_attributes_topic": state_topic,
        # The status message is retained, so without this a stale payload keeps
        # asserting health forever. Belinda published "ok": true on 2026-05-27
        # and every run after that aborted before reaching the publish, so Home
        # Assistant showed green for four months while nothing replicated.
        # Past this many seconds with no fresh message the entity goes
        # unavailable, which is the truthful state.
        "expire_after": {{ backups_zfs_server_mqtt_expire_after }},
    })
    cmd = ["mosquitto_pub", "-h", mqtt_host, "-t", discovery_topic, "-m", payload, "-r"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10, check=False)
        if result.returncode != 0:
            error(f"mosquitto_pub discovery failed: {result.stderr.decode().strip()}")
    except Exception as e:
        error(f"Failed to publish MQTT discovery: {e}")


def local_dataset_exists(dataset):
    """Whether a local dataset exists at all, as opposed to being out of date."""
    result = subprocess.run(
        ["zfs", "list", "-H", "-o", "name", dataset],
        capture_output=True, check=False
    )
    return result.returncode == 0


def get_local_backup_datasets(name, datasets, destination):
    """Return all local datasets under this host's backup destination.

    Expands each requested dataset to include its local children, so that
    discovered children (pulled via snapshots_discover_children) are reported.
    """
    result_datasets = []
    for dataset in datasets:
        local_parent = f"{destination}/{name}/{dataset}"
        try:
            result = subprocess.run(
                ["zfs", "list", "-H", "-o", "name", "-r", local_parent],
                capture_output=True, check=False
            )
            if result.returncode == 0:
                children = result.stdout.decode().strip().splitlines()
                # Strip the destination prefix to get relative dataset names
                prefix = f"{destination}/{name}/"
                result_datasets.extend(
                    ds[len(prefix):] for ds in children if ds.startswith(prefix)
                )
            else:
                result_datasets.append(dataset)
        except Exception:
            result_datasets.append(dataset)
    return result_datasets


def publish_mqtt_status(name, datasets, destination, mqtt_host, mqtt_topic_prefix, stale_multiplier=2, failure=None):
    """Publish pull status to MQTT after a successful pull."""
    now = datetime.now()
    stale_threshold = timedelta(hours=stale_multiplier * 2)

    all_datasets = get_local_backup_datasets(name, datasets, destination)

    missing_datasets = []
    stale_datasets = []
    healthy_datasets = []
    for dataset in all_datasets:
        local_ds = f"{destination}/{name}/{dataset}"
        # A dataset that has never replicated is not late, it is absent, and
        # the two need different responses. Reported together they are
        # indistinguishable: mail-archive-server and charlie/financial sat
        # among genuinely stale entries for weeks without anyone noticing
        # they had no copy at all.
        if not local_dataset_exists(local_ds):
            missing_datasets.append(dataset)
            continue
        newest_time = get_newest_autosnap_time(local_ds)
        if newest_time is None or (now - newest_time) > stale_threshold:
            stale_datasets.append(dataset)
        else:
            healthy_datasets.append(dataset)

    topic = f"{mqtt_topic_prefix}/{name}/backups"
    payload = json.dumps({
        "ok": len(stale_datasets) == 0 and len(missing_datasets) == 0 and failure is None,
        "host": name,
        "pulled_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "failure": failure,
        "missing_datasets": missing_datasets,
        "stale_datasets": stale_datasets,
        "healthy_datasets": healthy_datasets,
    })

    cmd = ["mosquitto_pub", "-h", mqtt_host, "-t", topic, "-m", payload, "-r"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10, check=False)
        if result.returncode != 0:
            error(f"mosquitto_pub failed: {result.stderr.decode().strip()}")
        else:
            debug(f"Published MQTT status to {topic}")
    except Exception as e:
        error(f"Failed to publish MQTT status: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backup ZFS datasets from a remote host.')
    parser.add_argument('--host', help='Remote host address for SSH')
    parser.add_argument('--name', help='Name used for local dataset path (defaults to --host)')
    parser.add_argument('--datasets', nargs='+', help='Source datasets')
    parser.add_argument('--user', default=DEFAULT_user, help='Remote SSH user')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Local dataset to receive backups (default: %(default)s)')
    parser.add_argument('--debug', default=DEFAULT_debug, help='Debug code', action=argparse.BooleanOptionalAction)
    parser.add_argument('--quiet', '-q', default=DEFAULT_quiet, help='Suppress informational output (errors still shown)', action=argparse.BooleanOptionalAction)
    parser.add_argument('--mqtt-host', type=str, default=None, help='MQTT broker hostname (enables MQTT publish)')
    parser.add_argument('--mqtt-topic-prefix', type=str, default='homeinfra/monitoring/zfs', help='MQTT topic prefix')
    parser.add_argument('--mqtt-name', type=str, default=None, help='Host name to use in MQTT topic (defaults to --name)')
    args = parser.parse_args()

    _quiet = args.quiet
    _debug = args.debug

    if not args.user or not args.host or not args.datasets:
        print("Usage: zfs-pull-backups --user <user> --host <host> --datasets-source <space-seperated list> [--datasets-destination <destination>]", file=sys.stderr)
        sys.exit(1)

    name = args.name if args.name else args.host

    # Set host-specific lockfile to allow parallel pulls from different hosts
    _lockfile = get_lockfile_path(name)

    # Acquire lockfile to prevent concurrent executions from this host.
    #
    # A blocked run used to exit 0 unconditionally, and the wrapper pings the
    # healthcheck on a zero exit, so a wedged lock reported success on every
    # cron tick and nothing ever went red. A brief overlap is normal and still
    # exits quietly — an initial send of a large dataset legitimately outlasts
    # the next tick. A lock held past the threshold is not an overlap, it is a
    # stuck run, and that has to be loud.
    if not acquire_lock():
        held_for = lockfile_age_hours()
        if held_for is not None and held_for >= STALE_LOCK_HOURS:
            stuck = (f"lockfile held for {held_for:.1f}h, over the {STALE_LOCK_HOURS}h "
                     f"threshold: the previous run is wedged and nothing is replicating")
            error(stuck)
            if args.mqtt_host:
                mqtt_name = args.mqtt_name if args.mqtt_name else name
                publish_mqtt_discovery(mqtt_name, args.mqtt_host, args.mqtt_topic_prefix)
                publish_mqtt_status(
                    name=mqtt_name,
                    datasets=args.datasets,
                    destination=args.destination,
                    mqtt_host=args.mqtt_host,
                    mqtt_topic_prefix=args.mqtt_topic_prefix,
                    stale_multiplier={{ backups_zfs_server_stale_threshold_multiplier }},
                    failure=stuck,
                )
            sys.exit(1)
        info("Another instance is still running; leaving it to finish.")
        sys.exit(0)

    # Register cleanup handlers
    atexit.register(release_lock)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    # Any dataset failing aborts the whole run, and the status publish used to
    # sit after it, so a failed run left the previous retained message in
    # place. That message is what Home Assistant reads, so a run that pulled
    # nothing kept asserting the last healthy result. Publish either way, and
    # say which failure ended the run.
    failure = None
    exit_code = 0
    try:
        preflight(args.host, name, args.datasets, args.user, args.destination)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
        if exit_code != 0:
            failure = f"pull aborted with exit {exit_code}"

    if args.mqtt_host:
        mqtt_name = args.mqtt_name if args.mqtt_name else name
        publish_mqtt_discovery(mqtt_name, args.mqtt_host, args.mqtt_topic_prefix)
        publish_mqtt_status(
            name=mqtt_name,
            datasets=args.datasets,
            destination=args.destination,
            mqtt_host=args.mqtt_host,
            mqtt_topic_prefix=args.mqtt_topic_prefix,
            stale_multiplier={{ backups_zfs_server_stale_threshold_multiplier }},
            failure=failure,
        )

    sys.exit(exit_code)
