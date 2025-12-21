#!/usr/bin/env python3
import subprocess
import sys
import argparse

DEFAULT_destination = "backuppool"
DEFAULT_mode = "push"

def preflight(host, user, datasets, destination, mode):
    # Check ability to connect to remote host
    
    # Check for source
    
    # Check for destination
    
    # All passed - start backup
    sendreceive_init(host, user, datasets, destination, mode)

def sendreceive(host, user, dataset, destination, mode):
    try:
        zfs_find_latest_snapshot = "zfs list -t snapshot -H -o name -S creation -r {dataset} | head -n 1"   

        # Construct the ZFS send and receive command
        if mode == 'push':
            # Push datasets to an offsite location
            sendoptions = "--dryrun --raw"
            receiveoptions = ""
            # zfs_find_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset} | head -n 1"   
            snapshot_name = subprocess.check_call(zfs_find_latest_snapshot, shell=True)
            zfscommand = f"zfs send {sendoptions} {dataset}@{snapshot_name} | ssh {user}@{host} zfs receive {receiveoptions} {destination}/{host}/{dataset}"
        elif mode == 'pull':
            # Pull datasets from production machines
            sendoptions = "--dryrun"
            receiveoptions = ""
            # zfs_find_latest_snapshot = f"ssh {host} zfs list -t snapshot -H -o name -S creation -r {dataset} | head -n 1"   
            snapshot_name = subprocess.check_call(zfs_find_latest_snapshot, shell=True)
            zfscommand = f"ssh {user}@{host} zfs send {sendoptions} {dataset}@{snapshot_name} | zfs receive {receiveoptions} {destination}/{host}/{dataset}"
        else:
            print("Invalid mode specified", file=sys.stderr)
            sys.exit(1)


        # Execute the command
        # subprocess.check_call(zfscommand, shell=True)
        print(f"{zfscommand}")
    except subprocess.CalledProcessError as e:
        print(f"Error during backup of {host}:{dataset}: {e}", file=sys.stderr)


def sendreceive_init(user, host, datasets, destination, mode):
    for dataset in datasets:
        sendreceive(host, user, dataset, destination, mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Push or pull ZFS backups from a remote host')
    parser.add_argument('--user', help='Remote SSH user')
    parser.add_argument('--host', help='Remote host')
    parser.add_argument('--datasets', nargs='+', help='Source datasets')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Destination dataset to receive backups (default: %(default)s)')
    parser.add_argument('--mode', help='Either push or pull from server')

    args = parser.parse_args()

    if not args.user or not args.host or not args.datasets:
        print("Usage: pull-zfs-backups.py --mode <mode> --user <user> --host <host> --datasets <space-seperated list> [--datasets <destination>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.user, args.host, args.datasets, args.destination, args.mode)
