#!/usr/bin/env python3
import subprocess
import sys
import argparse

DEFAULT_destination = "{{ zfsbackup_dataset }}"

def preflight(host, user, datasets, destination):
    # Check ability to connect to remote host
    
    # Check for source
    
    # Check for destination
    
    # All passed - start backup
    pulldatasets_init(host, user, datasets, destination)

def pulldatasets(host, user, dataset, destination):
    zfs_find_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset}"
    print("DEBUG zfs_find_latest_snapshot: " + zfs_find_latest_snapshot)

    # Construct the ZFS send and receive command

    # Pull datasets from production machines
    sendoptions = "--dryrun --raw"
    receiveoptions = ""
    zfs_find_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset}"
    try:
        ssh = subprocess.Popen(["ssh", "%s" % host, zfs_find_latest_snapshot],
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
        result = ssh.stdout.readlines()
        latest_snapshot = result.splitlines()[0]
    except subprocess.CalledProcessError as e:
        print("ERROR:\n", e.output)
        sys.exit(1)

    zfscommand = f"ssh {user}@{host} zfs send {sendoptions} {dataset}@{latest_snapshot} | zfs receive {receiveoptions} {destination}/{host}/{dataset}"

    # Execute the command
    print("DEBUG zfscommand: " + zfscommand)
    # subprocess.check_call(zfscommand, shell=True)


def pulldatasets_init(user, host, datasets, destination):
    for dataset in datasets:
        pulldatasets(host, user, dataset, destination)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Push or pull ZFS backups from a remote host')
    parser.add_argument('--user', help='Remote SSH user')
    parser.add_argument('--host', help='Remote host')
    parser.add_argument('--datasets', nargs='+', help='Source datasets')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Local dataset to receive backups (default: %(default)s)')

    args = parser.parse_args()

    if not args.user or not args.host or not args.datasets:
        print("Usage: zfs-pull-backups --user <user> --host <host> --datasets-source <space-seperated list> [--datasets-destination <destination>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.user, args.host, args.datasets, args.destination)
