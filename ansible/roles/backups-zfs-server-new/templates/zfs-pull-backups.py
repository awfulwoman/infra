#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse

DEFAULT_destination = "{{ backups_zfs_server_dataset }}"
DEFAULT_user="{{ vault_zfsbackups_user }}"
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
        
def preflight(host, datasets, user, destination):
    try:
        info(f'Checking {host} is up')
        subprocess.run(['ssh', f'{user}@{host}', 'ls'],
                shell=False, 
                check=True,
                capture_output=True
                )
    
        for dataset in datasets:
            info(f'Checking remote {dataset} exists')
            subprocess.run(
                ['ssh', f'{user}@{host}', f'zfs list {dataset}'],
                shell=False, 
                check=True,
                capture_output=True
                )
            
        info(f'Checking local {destination} exist')
        subprocess.run(['zfs', 'list', f'{destination}'],
                shell=False, 
                check=True,
                capture_output=True
                )
            
    except subprocess.CalledProcessError as e:        
        error("Errors detected in preflight checks. Aborting.")
        debug(f"{e}")
        sys.exit(1)

    pulldatasets_init(host, datasets, user, destination)

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
        error(f"Could not list remote datasets:\n", e.stderr.decode())
        sys.exit(1)


def pulldatasets_init(host, datasets, user, destination):
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

    info(f"Backing up {len(unique_datasets)} datasets individually")
    for dataset in unique_datasets:
        pulldatasets(host, dataset, user, destination)
    print('')
        
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
        error("Could not list remote snapshots:\n", e.stderr.decode())
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


def pulldatasets(host, dataset, user, destination):
    local_dataset = f"{destination}/{host}/{dataset}"

    remote_snapshots = get_remote_snapshots(host, dataset, user)
    if not remote_snapshots:
        print(f"ERROR: No snapshots found on remote for {dataset}")
        sys.exit(1)

    local_snapshots = get_local_snapshots(local_dataset)

    earliest_remote = remote_snapshots[0]
    latest_remote = remote_snapshots[-1]

    # Find common snapshots between local and remote
    common_snapshots = [s for s in local_snapshots if s in remote_snapshots]

    if not common_snapshots:
        # Initial sync: no common snapshots, need full send
        info(f"No common snapshots found. Performing initial sync for {host} - {dataset}")
        info(f"Remote has {len(remote_snapshots)} snapshots: {earliest_remote} -> {latest_remote}")

        # Step 1: Full send of earliest snapshot
        info(f"Pulling earliest snapshot from {host} - '{dataset}@{earliest_remote}'")
        send_cmd = f"ssh {user}@{host} zfs send {dataset}@{earliest_remote}"
        receive_cmd = f"zfs receive -F -u {local_dataset}"

        if not send_and_receive(send_cmd, receive_cmd):
            sys.exit(1)
        info(f"Successfully received earliest snapshot from {host}")
        debug(f"{dataset}@{earliest_remote}")

        # Step 2: Incremental from earliest to latest (if more than one snapshot)
        if earliest_remote != latest_remote:
            info(f"Pulling incremental snapshots between '{earliest_remote}' and '{latest_remote}'")
            send_cmd = f"ssh {user}@{host} zfs send -I {dataset}@{earliest_remote} {dataset}@{latest_remote}"

            if not send_and_receive(send_cmd, receive_cmd):
                sys.exit(1)
            info(f"Successfully received all snapshots up to '{latest_remote}'")
        else:
            info("Only one snapshot exists, no incremental receive needed.")

    else:
        # Incremental sync: find latest common snapshot and sync from there
        latest_common = common_snapshots[-1]

        if latest_common == latest_remote:
            info(f"Already up to date with {host} - {dataset}")
            debug(f"Latest is {dataset}@{latest_remote}")
            return

        info(f"Pulling incremental snapshots.")
        debug(f"{latest_common}' -> '{latest_remote}")
        send_cmd = f"ssh {user}@{host} zfs send -I {dataset}@{latest_common} {dataset}@{latest_remote}"
        receive_cmd = f"zfs receive -F -u {local_dataset}"

        if not send_and_receive(send_cmd, receive_cmd):
            sys.exit(1)
        info(f"Successfully synced up to '{latest_remote}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backup ZFS datasets from a remote host.')
    parser.add_argument('--host', help='Remote host')
    parser.add_argument('--datasets', nargs='+', help='Source datasets')
    parser.add_argument('--user', default=DEFAULT_user, help='Remote SSH user')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Local dataset to receive backups (default: %(default)s)')
    parser.add_argument('--debug', default=DEFAULT_debug, help='Debug code', action=argparse.BooleanOptionalAction)
    parser.add_argument('--quiet', '-q', default=DEFAULT_quiet, help='Suppress informational output (errors still shown)', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    _quiet = args.quiet
    _debug = args.debug

    if not args.user or not args.host or not args.datasets:
        print("Usage: zfs-pull-backups --user <user> --host <host> --datasets-source <space-seperated list> [--datasets-destination <destination>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.host, args.datasets, args.user, args.destination)
