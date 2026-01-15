#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse
from datetime import datetime, timedelta
import re

DEFAULT_user="{{ vault_zfsbackups_user }}"
DEFAULT_strip_prefix = "{{ backups_zfs_server_local_dataset }}"
DEFAULT_debug = False
DEFAULT_quiet = False
DEFAULT_bwlimit = None  # No bandwidth limit by default

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


def parse_size_to_bytes(size_str):
    """Parse a human-readable size string to bytes.

    Supports formats like: 1.5G, 500M, 100K, 1T, 1.2GiB, etc.
    """
    size_str = size_str.strip().upper()
    match = re.match(r'^([\d.]+)\s*([KMGTP])?I?B?$', size_str)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2) or ''

    multipliers = {
        '': 1,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
        'P': 1024 ** 5,
    }
    return int(value * multipliers.get(unit, 1))


def format_bytes(size_bytes):
    """Format bytes as human-readable string."""
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PiB"


def format_duration(seconds):
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def get_send_size(dataset, snapshot, incremental_from=None):
    """Get estimated size of a zfs send operation using -nv (dry run).

    Returns size in bytes, or None if estimation fails.

    OpenZFS output format (stdout):
        full    pool/data@snap    1234567890
        size    1234567890
    The 'size' line contains the total bytes to transfer.
    """
    if incremental_from:
        cmd = f"zfs send -nv -Rw -I {dataset}@{incremental_from} {dataset}@{snapshot}"
    else:
        cmd = f"zfs send -nv -Rw {dataset}@{snapshot}"

    debug(f"Estimating size: {cmd}")

    try:
        result = subprocess.run(
            cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        # OpenZFS outputs to stdout, some versions to stderr - check both
        output = result.stdout.decode() + result.stderr.decode()
        debug(f"Size estimation output: {output.strip()}")

        # Look for "size\t<bytes>" line (OpenZFS format)
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 2 and parts[0] == 'size':
                try:
                    return int(parts[1])
                except ValueError:
                    pass

        # Fallback: look for "total estimated size is X" (older format)
        match = re.search(r'total estimated size is\s+([\d.]+\s*[KMGTP]?)', output, re.IGNORECASE)
        if match:
            return parse_size_to_bytes(match.group(1))

        # Last resort: try last column of last non-empty line
        lines = [l for l in output.strip().split('\n') if l.strip()]
        if lines:
            parts = lines[-1].split()
            if parts:
                try:
                    return int(parts[-1])
                except ValueError:
                    return parse_size_to_bytes(parts[-1])

        return None

    except subprocess.CalledProcessError as e:
        debug(f"Could not estimate send size: {e.stderr.decode()}")
        return None


def preflight(host, datasets, user, destination, strip_prefix):
    # Check pv is available if bandwidth limiting is requested
    if _bwlimit:
        debug('Checking pv is installed for bandwidth limiting')
        result = subprocess.run(['which', 'pv'],
                shell=False,
                check=False,
                capture_output=True
                )
        if result.returncode != 0:
            error('pv is required for bandwidth limiting but not found.')
            sys.exit(1)
        info(f'Bandwidth limit set to {_bwlimit}')

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
        debug(f'Checking local source {dataset} exists')
        result = subprocess.run(
            ['zfs', 'list', dataset],
            shell=False,
            check=False,
            capture_output=True
            )
        if result.returncode != 0:
            error(f'Local dataset {dataset} does not exist\n  zfs: {result.stderr.decode().strip()}')
            sys.exit(1)
        debug(f'{dataset} exists')

    debug(f'Checking remote destination dataset {destination} exists')
    result = subprocess.run(['ssh', f'{user}@{host}', f'zfs list {destination}'],
            shell=False,
            check=False,
            capture_output=True
            )
    if result.returncode != 0:
        error(f'Remote destination {destination} does not exist\n  zfs: {result.stderr.decode().strip()}')
        sys.exit(1)
    debug(f'Destination {destination} exists')

    pushdatasets_init(host, datasets, user, destination, strip_prefix)

def pushdatasets_init(host, datasets, user, destination, strip_prefix):
    for dataset in datasets:
        pushdatasets(host, dataset, user, destination, strip_prefix)


def get_local_snapshots(dataset):
    """Get all snapshot names for a local dataset, sorted by creation time."""
    command = f"zfs list -t snapshot -H -o name -s creation -r {dataset}"

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

        debug(f"Found {len(direct_snapshots)} local snapshots")

        return direct_snapshots

    except subprocess.CalledProcessError as e:
        error(f"Could not get local snapshots: {e.stderr.decode()}")
        sys.exit(1)


def get_remote_snapshots(host, dataset, user):
    """Get all snapshot names for a dataset on remote host, sorted by creation time."""
    command = f"ssh {user}@{host} zfs list -t snapshot -H -o name -s creation -r {dataset}"

    debug(command)

    try:
        result = subprocess.run(
            command.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False  # Don't fail if dataset doesn't exist
        )
        if result.returncode != 0:
            return []  # Dataset doesn't exist yet on remote

        snapshots = result.stdout.decode().strip().splitlines()
        # Filter to only direct snapshots of this dataset (not child datasets)
        direct_snapshots = [s.split("@")[1] for s in snapshots if s.startswith(f"{dataset}@")]

        debug(f"Found {len(direct_snapshots)} remote snapshots")

        return direct_snapshots

    except Exception as e:
        debug(f"Error getting remote snapshots: {e}")
        return []


def ensure_remote_parent_exists(host, dataset, user):
    """Ensure parent dataset exists on remote, creating each level with canmount=off."""
    parent = "/".join(dataset.split("/")[:-1])
    if not parent:
        return True  # No parent needed (top-level dataset)

    # Build list of ancestors that need to be checked/created
    # e.g., for "pool/a/b/c" we need to check: pool, pool/a, pool/a/b, pool/a/b/c
    parts = parent.split("/")
    ancestors = []
    for i in range(1, len(parts) + 1):
        ancestors.append("/".join(parts[:i]))

    for ancestor in ancestors:
        # Check if this ancestor exists
        check_cmd = f"ssh {user}@{host} zfs list {ancestor}"
        debug(f"Checking if {ancestor} exists")

        result = subprocess.run(
            check_cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )

        if result.returncode == 0:
            debug(f"{ancestor} already exists")
            continue

        # Create this single level with canmount=off
        # Not using -p so that we control the properties on each level
        info(f"Creating remote dataset: {ancestor}")
        create_cmd = f"ssh {user}@{host} zfs create -o canmount=off {ancestor}"
        debug(create_cmd)

        try:
            subprocess.run(
                create_cmd.split(' '),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
        except subprocess.CalledProcessError as e:
            error(f"Failed to create remote dataset {ancestor}: {e.stderr.decode()}")
            return False

    return True


def send_and_receive(send_cmd, receive_cmd):
    """Execute a zfs send | ssh zfs receive pipeline using streaming (no memory buffering).

    If _bwlimit is set, inserts pv for bandwidth throttling:
        zfs send | pv -L <rate> | ssh zfs receive
    """
    try:
        debug(f"{send_cmd}")
        if _bwlimit:
            debug(f"pv -q -L {_bwlimit}")
        debug(f"{receive_cmd}")

        # Create a true pipeline: send.stdout -> [pv ->] receive.stdin
        # This streams data directly without buffering in memory
        send_proc = subprocess.Popen(
            send_cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # If bandwidth limiting is enabled, insert pv in the pipeline
        if _bwlimit:
            # pv -q (quiet) -L <rate> limits bandwidth
            # Rate format: 100k, 10m, 1g for KB/s, MB/s, GB/s
            pv_proc = subprocess.Popen(
                ['pv', '-q', '-L', _bwlimit],
                stdin=send_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Allow send_proc to receive SIGPIPE if pv exits
            send_proc.stdout.close()

            receive_proc = subprocess.Popen(
                receive_cmd.split(' '),
                stdin=pv_proc.stdout,
                stderr=subprocess.PIPE
            )
            # Allow pv_proc to receive SIGPIPE if receive_proc exits
            pv_proc.stdout.close()
        else:
            pv_proc = None
            receive_proc = subprocess.Popen(
                receive_cmd.split(' '),
                stdin=send_proc.stdout,
                stderr=subprocess.PIPE
            )
            # Allow send_proc to receive SIGPIPE if receive_proc exits
            send_proc.stdout.close()

        # Wait for all processes to complete and capture stderr
        _, receive_stderr = receive_proc.communicate()

        pv_stderr = None
        if pv_proc:
            _, pv_stderr = pv_proc.communicate()

        _, send_stderr = send_proc.communicate()

        # Check if any part of the pipeline failed
        send_failed = send_proc.returncode != 0
        pv_failed = pv_proc and pv_proc.returncode != 0
        receive_failed = receive_proc.returncode != 0

        if send_failed or pv_failed or receive_failed:
            # Report which component(s) failed
            if send_failed:
                error(f"zfs send failed with code {send_proc.returncode}")
            if pv_failed:
                error(f"pv (bandwidth limiter) failed with code {pv_proc.returncode}")
            if receive_failed:
                error(f"zfs receive failed with code {receive_proc.returncode}")

            # Report all captured stderr (the real error is often in receive)
            if send_stderr and send_stderr.strip():
                error(f"  send stderr: {send_stderr.decode().strip()}")
            if pv_stderr and pv_stderr.strip():
                error(f"  pv stderr: {pv_stderr.decode().strip()}")
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


def pushdatasets(host, dataset, user, destination, strip_prefix):
    # Strip the local backup prefix from the dataset path
    # e.g., if dataset is "slowpool/encryptedbackups/host-storage/fastpool/data"
    # and strip_prefix is "slowpool/encryptedbackups", the relative path becomes
    # "host-storage/fastpool/data"
    if strip_prefix and dataset.startswith(strip_prefix + "/"):
        relative_path = dataset[len(strip_prefix) + 1:]
    else:
        relative_path = dataset

    remote_dataset = f"{destination}/{relative_path}"
    info(f"Pushing {dataset} -> {remote_dataset}")

    # Ensure parent dataset exists on remote
    if not ensure_remote_parent_exists(host, remote_dataset, user):
        sys.exit(1)

    local_snapshots = get_local_snapshots(dataset)
    if not local_snapshots:
        error(f"No snapshots found locally for {dataset}")
        sys.exit(1)

    remote_snapshots = get_remote_snapshots(host, remote_dataset, user)

    earliest_local = local_snapshots[0]
    latest_local = local_snapshots[-1]

    # Find common snapshots between local and remote
    common_snapshots = [s for s in remote_snapshots if s in local_snapshots]

    if not common_snapshots:
        # Initial sync: no common snapshots, need full send
        start_time = datetime.now()
        info(f"No remote snapshots found. Performing initial sync for {dataset}")
        info(f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        info(f"Local has {len(local_snapshots)} snapshots: {earliest_local} -> {latest_local}")

        # Estimate total transfer size
        total_size = 0
        initial_size = get_send_size(dataset, earliest_local)
        if initial_size:
            total_size += initial_size

        if earliest_local != latest_local:
            incremental_size = get_send_size(dataset, latest_local, incremental_from=earliest_local)
            if incremental_size:
                total_size += incremental_size

        if total_size > 0:
            size_msg = f"Estimated total size: {format_bytes(total_size)}"
            if _bwlimit:
                bwlimit_bytes = parse_size_to_bytes(_bwlimit)
                if bwlimit_bytes:
                    estimated_seconds = total_size / bwlimit_bytes
                    size_msg += f" (ETA: {format_duration(estimated_seconds)} at {_bwlimit}/s)"
            info(size_msg)

        # Step 1: Full send of earliest snapshot (raw for encrypted datasets)
        info(f"Pushing earliest snapshot '{earliest_local}'")
        send_cmd = f"zfs send -Rw {dataset}@{earliest_local}"
        receive_cmd = f"ssh {user}@{host} zfs receive -F -u {remote_dataset}"

        if not send_and_receive(send_cmd, receive_cmd):
            sys.exit(1)
        info(f"Successfully pushed earliest snapshot '{earliest_local}'")

        # Step 2: Incremental from earliest to latest (if more than one snapshot)
        if earliest_local != latest_local:
            info(f"Pushing incremental '{earliest_local}' -> '{latest_local}'")
            send_cmd = f"zfs send -Rw -I {dataset}@{earliest_local} {dataset}@{latest_local}"

            if not send_and_receive(send_cmd, receive_cmd):
                sys.exit(1)
            info(f"Successfully pushed all snapshots up to '{latest_local}'")
        else:
            info("Only one snapshot exists, no incremental needed.")

        end_time = datetime.now()
        elapsed = end_time - start_time
        info(f"Completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (elapsed: {elapsed})")

    else:
        # Incremental sync: find latest common snapshot and sync from there
        latest_common = common_snapshots[-1]
        debug(f"Found {len(common_snapshots)} common snapshots. Latest: {latest_common}")

        if latest_common == latest_local:
            info(f"Up-to-date - {dataset}")
            debug(f"Latest is {dataset}@{latest_local}")
            return

        info(f"Pushing incremental snapshots.")
        debug(f"{latest_common}' -> '{latest_local}")
        send_cmd = f"zfs send -Rw -I {dataset}@{latest_common} {dataset}@{latest_local}"
        receive_cmd = f"ssh {user}@{host} zfs receive -F -u {remote_dataset}"

        if not send_and_receive(send_cmd, receive_cmd):
            sys.exit(1)
        info(f"Successfully synced up to '{latest_local}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Push ZFS datasets to a remote host.')
    parser.add_argument('--host', help='Remote host to push to')
    parser.add_argument('--datasets', nargs='+', help='Local source datasets to push')
    parser.add_argument('--user', default=DEFAULT_user, help='Remote SSH user')
    parser.add_argument('--destination', required=True, help='Remote dataset to receive backups')
    parser.add_argument('--strip-prefix', default=DEFAULT_strip_prefix, help='Prefix to strip from dataset paths (default: %(default)s)')
    parser.add_argument('--debug', default=DEFAULT_debug, help='Debug code', action=argparse.BooleanOptionalAction)
    parser.add_argument('--quiet', '-q', default=DEFAULT_quiet, help='Suppress informational output (errors still shown)', action=argparse.BooleanOptionalAction)
    parser.add_argument('--bwlimit', default=DEFAULT_bwlimit, help='Bandwidth limit for transfers (requires pv). Format: 100k, 10m, 1g for KB/s, MB/s, GB/s')
    args = parser.parse_args()

    _quiet = args.quiet
    _debug = args.debug
    _bwlimit = args.bwlimit

    if not args.user or not args.host or not args.datasets or not args.destination:
        print("Usage: zfs-push-backups --host <host> --datasets <space-separated list> --destination <remote-dataset> [--user <user>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.host, args.datasets, args.user, args.destination, args.strip_prefix)
