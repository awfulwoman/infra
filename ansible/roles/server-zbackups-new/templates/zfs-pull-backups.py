#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse

DEFAULT_destination = "{{ zfsbackup_dataset }}"
DEFAULT_user="{{ vault_zfsbackups_user }}"
DEFAULT_debug = False

def preflight(host, datasets, user, destination, debug): 
    try:
        print('Checking host is up')
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
            
        print('Checking backup root dataset exist')
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

def pulldatasets_init(host, datasets, user, destination, debug):
    for dataset in datasets:
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
    """Execute a zfs send | zfs receive pipeline."""
    try:
        if debug:
            print(f"DEBUG: {send_cmd}")
            print(f"DEBUG: {receive_cmd}")

        send_result = subprocess.run(
            send_cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        subprocess.run(
            receive_cmd.split(' '),
            input=send_result.stdout,
            check=True
        )
        return True

    except subprocess.CalledProcessError as e:
        print('#############################')
        print(f"ERROR: Transfer failed.\n{e}")
        if e.stderr:
            print(e.stderr.decode())
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
        print(f"No local snapshots found. Performing initial sync for {dataset}")
        print(f"Remote has {len(remote_snapshots)} snapshots: {earliest_remote} -> {latest_remote}")

        # Step 1: Full send of earliest snapshot
        print(f"Step 1: Pulling earliest snapshot '{earliest_remote}'")
        send_cmd = f"ssh {user}@{host} zfs send -R {dataset}@{earliest_remote}"
        receive_cmd = f"zfs receive -F {local_dataset}"

        if not send_and_receive(send_cmd, receive_cmd, debug):
            sys.exit(1)
        print(f"Successfully received earliest snapshot '{earliest_remote}'")

        # Step 2: Incremental from earliest to latest (if more than one snapshot)
        if earliest_remote != latest_remote:
            print(f"Step 2: Pulling incremental '{earliest_remote}' -> '{latest_remote}'")
            send_cmd = f"ssh {user}@{host} zfs send -R -I {dataset}@{earliest_remote} {dataset}@{latest_remote}"

            if not send_and_receive(send_cmd, receive_cmd, debug):
                sys.exit(1)
            print(f"Successfully received all snapshots up to '{latest_remote}'")
        else:
            print("Only one snapshot exists, no incremental needed.")

    else:
        # Incremental sync: find latest common snapshot and sync from there
        latest_common = common_snapshots[-1]
        print(f"Found {len(common_snapshots)} common snapshots. Latest: {latest_common}")

        if latest_common == latest_remote:
            print(f"Already up to date with '{latest_remote}'")
            return

        print(f"Pulling incremental '{latest_common}' -> '{latest_remote}'")
        send_cmd = f"ssh {user}@{host} zfs send -R -I {dataset}@{latest_common} {dataset}@{latest_remote}"
        receive_cmd = f"zfs receive -F {local_dataset}"

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
