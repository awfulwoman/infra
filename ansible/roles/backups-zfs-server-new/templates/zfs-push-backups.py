#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse

DEFAULT_user="{{ vault_zfsbackups_user }}"
DEFAULT_strip_prefix = "{{ backups_zfs_server_local_dataset }}"
DEFAULT_debug = False
DEFAULT_quiet = False

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

def preflight(host, datasets, user, destination, strip_prefix):
    try:
        info('Checking remote host is up')
        result = subprocess.run(['ssh', f'{user}@{host}', 'ls'],
                shell=False,
                check=True,
                capture_output=True
                )
        if result.returncode != 0:
            error(f'Could not connect to {host}')
        else:
            info(f'{host} is up')

        for dataset in datasets:
            debug(f'Checking local source {dataset} exists')
            result = subprocess.run(
                ['zfs', 'list', dataset],
                shell=False,
                check=True,
                capture_output=True
                )
            if result.returncode != 0:
                error(f'{dataset} does not exist')
            else:
                debug(f'{dataset} exists')

        debug(f'Checking remote destination dataset {destination} exists')
        result = subprocess.run(['ssh', f'{user}@{host}', f'zfs list {destination}'],
                shell=False,
                check=True,
                capture_output=True
                )
        if result.returncode != 0:
            error(f'Remote destination ({destination}) does not exist')
        else:
            debug(f'Destination {destination} exists')

    except subprocess.CalledProcessError as e:
        error("Errors detected in preflight checks. Aborting.")
        debug(f"{e}")
        sys.exit(1)

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
    """Execute a zfs send | ssh zfs receive pipeline using streaming (no memory buffering)."""
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

        if send_proc.returncode != 0:
            error(f"zfs send failed with code {send_proc.returncode}")
            if send_stderr:
                debug(send_stderr.decode())
            return False

        if receive_proc.returncode != 0:
            error(f"zfs receive failed with code {receive_proc.returncode}")
            if receive_stderr:
                debug(receive_stderr.decode())
            return False

        return True

    except Exception as e:
        error(f"Transfer failed!")
        debug(f'{e}')
        return False


def pushdatasets(host, dataset, user, destination, strip_prefix):
    # Strip the local backup prefix from the dataset path
    # e.g., if dataset is "backuppool/encryptedbackups/host-storage/fastpool/data"
    # and strip_prefix is "backuppool/encryptedbackups", the relative path becomes
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
        info(f"No remote snapshots found. Performing initial sync for {dataset}")
        info(f"Local has {len(local_snapshots)} snapshots: {earliest_local} -> {latest_local}")

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
    args = parser.parse_args()

    _quiet = args.quiet
    _debug = args.debug

    if not args.user or not args.host or not args.datasets or not args.destination:
        print("Usage: zfs-push-backups --host <host> --datasets <space-separated list> --destination <remote-dataset> [--user <user>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.host, args.datasets, args.user, args.destination, args.strip_prefix)
