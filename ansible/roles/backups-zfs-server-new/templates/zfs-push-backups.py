#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse

DEFAULT_user="{{ vault_zfsbackups_user }}"
DEFAULT_strip_prefix = "{{ backups_zfs_server_dataset }}"
DEFAULT_debug = False

def preflight(host, datasets, user, destination, strip_prefix, debug):
    try:
        print('Checking remote host is up')
        subprocess.run(['ssh', f'{user}@{host}', 'ls'],
                shell=False,
                check=True,
                capture_output=True
                )

        for dataset in datasets:
            print(f'Checking local source {dataset} exists')
            subprocess.run(
                ['zfs', 'list', dataset],
                shell=False,
                check=True,
                capture_output=True
                )

        print(f'Checking remote destination dataset {destination} exists')
        subprocess.run(['ssh', f'{user}@{host}', f'zfs list {destination}'],
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

    pushdatasets_init(host, datasets, user, destination, strip_prefix, debug)

def pushdatasets_init(host, datasets, user, destination, strip_prefix, debug):
    for dataset in datasets:
        pushdatasets(host, dataset, user, destination, strip_prefix, debug)


def get_local_snapshots(dataset, debug):
    """Get all snapshot names for a local dataset, sorted by creation time."""
    command = f"zfs list -t snapshot -H -o name -s creation -r {dataset}"

    if debug:
        print("DEBUG: Getting local snapshots via\n" + command)

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
            print(f"DEBUG: Found {len(direct_snapshots)} local snapshots")

        return direct_snapshots

    except subprocess.CalledProcessError as e:
        print("ERROR when obtaining local snapshots:\n", e.stderr.decode())
        sys.exit(1)


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
            check=False  # Don't fail if dataset doesn't exist
        )
        if result.returncode != 0:
            return []  # Dataset doesn't exist yet on remote

        snapshots = result.stdout.decode().strip().splitlines()
        # Filter to only direct snapshots of this dataset (not child datasets)
        direct_snapshots = [s.split("@")[1] for s in snapshots if s.startswith(f"{dataset}@")]

        if debug:
            print(f"DEBUG: Found {len(direct_snapshots)} remote snapshots")

        return direct_snapshots

    except Exception as e:
        if debug:
            print(f"DEBUG: Error getting remote snapshots: {e}")
        return []


def ensure_remote_parent_exists(host, dataset, user, debug):
    """Ensure parent dataset exists on remote, creating it if necessary."""
    parent = "/".join(dataset.split("/")[:-1])
    if not parent:
        return True  # No parent needed (top-level dataset)

    command = f"ssh {user}@{host} zfs list {parent}"
    if debug:
        print(f"DEBUG: Checking if remote parent exists: {command}")

    result = subprocess.run(
        command.split(' '),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False
    )

    if result.returncode == 0:
        if debug:
            print(f"DEBUG: Remote parent {parent} already exists")
        return True

    # Parent doesn't exist, create it (and any ancestors)
    print(f"Creating remote parent dataset: {parent}")
    create_cmd = f"ssh {user}@{host} zfs create -p {parent}"
    if debug:
        print(f"DEBUG: {create_cmd}")

    try:
        subprocess.run(
            create_cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create remote parent dataset: {e.stderr.decode()}")
        return False


def send_and_receive(send_cmd, receive_cmd, debug):
    """Execute a zfs send | ssh zfs receive pipeline using streaming (no memory buffering)."""
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
        print(f"ERROR: Transfer failed!\n{e}")
        print('#############################')
        return False


def pushdatasets(host, dataset, user, destination, strip_prefix, debug):
    # Strip the local backup prefix from the dataset path
    # e.g., if dataset is "backuppool/encryptedbackups/host-storage/fastpool/data"
    # and strip_prefix is "backuppool/encryptedbackups", the relative path becomes
    # "host-storage/fastpool/data"
    if strip_prefix and dataset.startswith(strip_prefix + "/"):
        relative_path = dataset[len(strip_prefix) + 1:]
    else:
        relative_path = dataset

    remote_dataset = f"{destination}/{relative_path}"
    print(f"Pushing {dataset} -> {remote_dataset}")

    # Ensure parent dataset exists on remote
    if not ensure_remote_parent_exists(host, remote_dataset, user, debug):
        sys.exit(1)

    local_snapshots = get_local_snapshots(dataset, debug)
    if not local_snapshots:
        print(f"ERROR: No snapshots found locally for {dataset}")
        sys.exit(1)

    remote_snapshots = get_remote_snapshots(host, remote_dataset, user, debug)

    earliest_local = local_snapshots[0]
    latest_local = local_snapshots[-1]

    # Find common snapshots between local and remote
    common_snapshots = [s for s in remote_snapshots if s in local_snapshots]

    if not common_snapshots:
        # Initial sync: no common snapshots, need full send
        print(f"No remote snapshots found. Performing initial sync for {dataset}")
        print(f"Local has {len(local_snapshots)} snapshots: {earliest_local} -> {latest_local}")

        # Step 1: Full send of earliest snapshot (raw for encrypted datasets)
        print(f"Step 1: Pushing earliest snapshot '{earliest_local}'")
        send_cmd = f"zfs send -Rw {dataset}@{earliest_local}"
        receive_cmd = f"ssh {user}@{host} zfs receive -F {remote_dataset}"

        if not send_and_receive(send_cmd, receive_cmd, debug):
            sys.exit(1)
        print(f"Successfully pushed earliest snapshot '{earliest_local}'")

        # Step 2: Incremental from earliest to latest (if more than one snapshot)
        if earliest_local != latest_local:
            print(f"Step 2: Pushing incremental '{earliest_local}' -> '{latest_local}'")
            send_cmd = f"zfs send -Rw -I {dataset}@{earliest_local} {dataset}@{latest_local}"

            if not send_and_receive(send_cmd, receive_cmd, debug):
                sys.exit(1)
            print(f"Successfully pushed all snapshots up to '{latest_local}'")
        else:
            print("Only one snapshot exists, no incremental needed.")

    else:
        # Incremental sync: find latest common snapshot and sync from there
        latest_common = common_snapshots[-1]
        print(f"Found {len(common_snapshots)} common snapshots. Latest: {latest_common}")

        if latest_common == latest_local:
            print(f"Already up to date with '{latest_local}'")
            return

        print(f"Pushing incremental '{latest_common}' -> '{latest_local}'")
        send_cmd = f"zfs send -Rw -I {dataset}@{latest_common} {dataset}@{latest_local}"
        receive_cmd = f"ssh {user}@{host} zfs receive -F {remote_dataset}"

        if not send_and_receive(send_cmd, receive_cmd, debug):
            sys.exit(1)
        print(f"Successfully synced up to '{latest_local}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Push ZFS datasets to a remote host.')
    parser.add_argument('--host', help='Remote host to push to')
    parser.add_argument('--datasets', nargs='+', help='Local source datasets to push')
    parser.add_argument('--user', default=DEFAULT_user, help='Remote SSH user')
    parser.add_argument('--destination', required=True, help='Remote dataset to receive backups')
    parser.add_argument('--strip-prefix', default=DEFAULT_strip_prefix, help='Prefix to strip from dataset paths (default: %(default)s)')
    parser.add_argument('--debug', default=DEFAULT_debug, help='Debug code', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if not args.user or not args.host or not args.datasets or not args.destination:
        print("Usage: zfs-push-backups --host <host> --datasets <space-separated list> --destination <remote-dataset> [--user <user>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.host, args.datasets, args.user, args.destination, args.strip_prefix, args.debug)
