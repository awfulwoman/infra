#!/usr/bin/env python3
import subprocess
import sys
import argparse

DEFAULT_destination = "{{ zfsbackup_dataset }}"

def preflight(host, user, datasets, destination, mode):
    # Check ability to connect to remote host
    
    # Check for source
    
    # Check for destination
    
    # All passed - start backup
    pushdatasets_init(host, user, datasets, destination, mode)

def pushdatasets(host, user, dataset, destination, mode):
    zfs_find_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset}"
    print("DEBUG zfs_find_latest_snapshot: " + zfs_find_latest_snapshot)

    # Construct the ZFS send and receive command
    # Push datasets to an offsite location
    sendoptions = "--dryrun --raw"
    receiveoptions = ""
    # zfs_find_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset} | head -n 1"   
    try:
        latest_snapshot = subprocess.check_output(zfs_find_latest_snapshot.split(' '))
        latest_snapshot = latest_snapshot.splitlines()[0]
    except subprocess.CalledProcessError as e:
        print("ERROR:\n", e.output)
        sys.exit(1)
    zfscommand = f"zfs send {sendoptions} {dataset}@{latest_snapshot} | ssh {user}@{host} zfs receive {receiveoptions} {destination}/{host}/{dataset}"

    # Execute the command
    print("DEBUG zfscommand: " + zfscommand)
    # subprocess.check_call(zfscommand, shell=True)

def pushdatasets_init(user, host, datasets, destination, mode):
    for dataset in datasets:
        pushdatasets(host, user, dataset, destination, mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Push or pull ZFS backups from a remote host')
    parser.add_argument('--user', help='Destination SSH user')
    parser.add_argument('--host', help='Destination host')
    parser.add_argument('--datasets', nargs='+', help='Local source datasets')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Dataset on remote host to receive backups (default: %(default)s)')

    args = parser.parse_args()

    if not args.user or not args.host or not args.datasets:
        print("Usage: zfs-push-backups --user <user> --host <host> --datasets-source <space-seperated list> --datasets-destination <destination>", file=sys.stderr)
        sys.exit(1)

    preflight(args.user, args.host, args.datasets, args.destination)
