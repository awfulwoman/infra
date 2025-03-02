#!/usr/bin/env python3

import subprocess
import sys
import argparse

DEFAULT_destination = "backuppool"

def pull_from_host(host, user, dataset, destination):
    try:
        
        # Find the latest snapshot
        zfs_find_latest_snapshot=  f"ssh {host} zfs list -t snapshot -H -o name -S creation -r tank | head -n 1"


        # Construct the ZFS send and receive command
        zfscommand = f"ssh {host} zfs send {user}@{dataset}@{snapshot} | zfs receive {destination}/{host}/{dataset}"
        
        # Execute the command
        # subprocess.check_call(zfscommand, shell=True)
        print(f"SIMULATED OUTPUT: {zfscommand}")

        print(f"Backup from {host}:{dataset} to {destination} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during backup of {host}:{dataset}: {e}", file=sys.stderr)


def pull_multiple_datasets(user, host, datasets, destination):
    # print(f"Looping over datasets {datasets}")
    for dataset in datasets:
        pull_from_host(host, user, dataset, destination)

if __name__ == "__main__":
    # if len(sys.argv) < 3:
    #     print("Usage: pull-zfs-backups.py --user <user> --host <host> --datasets <datasets> [<destination>]", file=sys.stderr)
    #     sys.exit(1)

    parser = argparse.ArgumentParser(description='Pull ZFS backups from a remote host.')
    parser.add_argument('--user', help='Remote user for SSH')
    parser.add_argument('--host', help='Remote host to pull from')
    parser.add_argument('--datasets', nargs='+', help='Remote datasets to pull')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Local pool to receive backups (default: %(default)s)')

    args = parser.parse_args()

    if not args.user or not args.host or not args.datasets:
        print("Usage: pull-zfs-backups.py --user <user> --host <host> --datasets <space-seperated list> [--datasets <destination>]", file=sys.stderr)
        sys.exit(1)

    pull_multiple_datasets(args.user, args.host, args.datasets, args.destination)