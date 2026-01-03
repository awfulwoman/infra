#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse

DEFAULT_destination = "{{ backups_zfs_server_dataset }}"
DEFAULT_user="{{ vault_zfsbackups_user }}"
DEFAULT_debug = False

def preflight(host, datasets, user, destination, debug): 
    try:
        print(f'Checking {host} is up')
        subprocess.run(['ssh', f'{user}@{host}', 'ls'],
                shell=False, 
                check=True,
                capture_output=True
                )
    
        for dataset in datasets:
            print(f'Checking remote {dataset} exists')
            subprocess.run(
                ['ssh', f'{user}@{host}', f'zfs list {dataset}'],
                shell=False, 
                check=True,
                capture_output=True
                )
            
        print(f'Checking local {destination} exist')
        subprocess.run(['zfs', 'list', f'{destination}'],
                shell=False, 
                check=True,
                capture_output=True
                )
            
    except subprocess.CalledProcessError as e:        
        print("Errors detected in preflight checks. Aborting.")
        if debug:
            print(f"DEBUG: {e}")
        print(" ")
        sys.exit(1)

    pulldatasets_init(host, datasets, user, destination, debug)

def get_remote_child_datasets(host, dataset, user, debug):
    """Get all datasets under a parent (including the parent itself)."""
    command = f"ssh {user}@{host} zfs list -H -o name -r {dataset}"

    if debug:
        print("DEBUG: " + command)

    try:
        result = subprocess.run(
            command.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        datasets = result.stdout.decode().strip().splitlines()

        if debug:
            print(f"DEBUG: Found {len(datasets)} datasets under {dataset}")

        return datasets

    except subprocess.CalledProcessError as e:
        print(f"ERROR when listing remote datasets:\n", e.stderr.decode())
        sys.exit(1)


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
        
def get_remote_snapshots(host, dataset, user, debug):
    """Get all snapshot names for a dataset on remote host, sorted by creation time."""
    command = f"ssh {user}@{host} zfs list -t snapshot -H -o name -s creation -r {dataset}"

    if debug:
        print("DEBUG: " + command)

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

        if debug:
            print(f"DEBUG: Found {len(direct_snapshots)} remote snapshots")

        return direct_snapshots

    except subprocess.CalledProcessError as e:
        print("ERROR when obtaining remote snapshots:\n", e.stderr.decode())
        sys.exit(1)


def get_local_snapshots(dataset, debug):
    """Get all snapshot names for a local dataset, sorted by creation time."""
    command = f"zfs list -t snapshot -H -o name -s creation -r {dataset}"

    if debug:
        print("DEBUG: " + command)

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

        if debug:
            print(f"DEBUG: Found {len(direct_snapshots)} local snapshots")

        return direct_snapshots

    except Exception as e:
        if debug:
            print(f"DEBUG: Error getting local snapshots: {e}")
        return []
        

def send_and_receive(send_cmd, receive_cmd, debug):
    """Execute a zfs send | zfs receive pipeline using streaming (no memory buffering)."""
    try:
        if debug:
            print(f"DEBUG: {send_cmd}")
            print(f"DEBUG: {receive_cmd}")

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
            print('#############################')
            print(f"ERROR: zfs send failed with code {send_proc.returncode}")
            if send_stderr:
                print(send_stderr.decode())
            print('#############################')
            return False

        if receive_proc.returncode != 0:
            print('#############################')
            print(f"ERROR: zfs receive failed with code {receive_proc.returncode}")
            if receive_stderr:
                print(receive_stderr.decode())
            print('#############################')
            return False

        return True

    except Exception as e:
        print('#############################')
        print(f"ERROR: Transfer failed.\n{e}")
        print('#############################')
        return False


def pulldatasets(host, dataset, user, destination, debug):
    local_dataset = f"{destination}/{host}/{dataset}"

    remote_snapshots = get_remote_snapshots(host, dataset, user, debug)
    if not remote_snapshots:
        print(f"ERROR: No snapshots found on remote for {dataset}")
        sys.exit(1)

    local_snapshots = get_local_snapshots(local_dataset, debug)

    earliest_remote = remote_snapshots[0]
    latest_remote = remote_snapshots[-1]

    # Find common snapshots between local and remote
    common_snapshots = [s for s in local_snapshots if s in remote_snapshots]

    if not common_snapshots:
        # Initial sync: no common snapshots, need full send
        print(f"No common snapshots found. Performing initial sync for {host} - {dataset}")
        print(f"Remote has {len(remote_snapshots)} snapshots: {earliest_remote} -> {latest_remote}")

        # Step 1: Full send of earliest snapshot
        print(f"Pulling earliest snapshot from {host} - '{dataset}@{earliest_remote}'")
        send_cmd = f"ssh {user}@{host} zfs send {dataset}@{earliest_remote}"
        receive_cmd = f"zfs receive -F -u {local_dataset}"

        if not send_and_receive(send_cmd, receive_cmd, debug):
            sys.exit(1)
        print(f"Successfully received earliest snapshot from {host} - '{dataset}@{earliest_remote}'")

        # Step 2: Incremental from earliest to latest (if more than one snapshot)
        if earliest_remote != latest_remote:
            print(f"Pulling incremental snapshots '{earliest_remote}' -> '{latest_remote}'")
            send_cmd = f"ssh {user}@{host} zfs send -I {dataset}@{earliest_remote} {dataset}@{latest_remote}"

            if not send_and_receive(send_cmd, receive_cmd, debug):
                sys.exit(1)
            print(f"Successfully received all snapshots up to '{latest_remote}'")
        else:
            print("Only one snapshot exists, no incremental needed.")

    else:
        # Incremental sync: find latest common snapshot and sync from there
        latest_common = common_snapshots[-1]
        # print(f"Found {len(common_snapshots)} common snapshots. Latest: {latest_common}")

        if latest_common == latest_remote:
            print(f"Already up to date with {host} - '{dataset}@{latest_remote}'")
            return

        print(f"Pulling incremental '{latest_common}' -> '{latest_remote}'")
        send_cmd = f"ssh {user}@{host} zfs send -I {dataset}@{latest_common} {dataset}@{latest_remote}"
        receive_cmd = f"zfs receive -F -u {local_dataset}"

        if not send_and_receive(send_cmd, receive_cmd, debug):
            sys.exit(1)
        print(f"Successfully synced up to '{latest_remote}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Pull ZFS datasets from a remote host.')
    parser.add_argument('--host', help='Remote host')
    parser.add_argument('--datasets', nargs='+', help='Source datasets')
    parser.add_argument('--user', default=DEFAULT_user, help='Remote SSH user')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Local dataset to receive backups (default: %(default)s)')
    parser.add_argument('--debug', default=DEFAULT_debug, help='Debug code', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if not args.user or not args.host or not args.datasets:
        print("Usage: zfs-pull-backups --user <user> --host <host> --datasets-source <space-seperated list> [--datasets-destination <destination>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.host, args.datasets, args.user, args.destination, args.debug)
