#! /opt/zfsbackup/bin/python
import subprocess
import sys
import argparse
import zfslib as zfs

DEFAULT_destination = "{{ zfsbackup_dataset }}"
DEFAULT_user="{{ vault_zfsbackups_user }}"

def preflight(host, datasets, user, destination):
    # Check ability to connect to remote host
    # connstring = f'{user}@{host}'
    # print(connstring)
    # conn = zfs.Connection(host=connstring)
    # poolset = conn.load_poolset()
    

    # p = poolset.get_pool('fastpool')
    # ds = p.get_dataset('compositions')
    # all_snaps = ds.get_all_snapshots()
    # if len(all_snaps) == 0:
    #     print('No snapshots found for dataset: {}'.format(ds))
    
    # Check for destination
    
    # All passed - start backup
    pulldatasets_init(host, datasets, user, destination)

def pulldatasets_init(host, datasets, user, destination):
    for dataset in datasets:
        pulldatasets(host, dataset, user, destination)
        
def get_latest_snapshot(host, dataset, user):
    command_ssh_connection = f"ssh {user}@{host}"
    command_zfs_get_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset}"
    command_get_latest_snapshot = command_ssh_connection + ' ' + command_zfs_get_latest_snapshot
    
    print("DEBUG: " + command_ssh_connection + ' ' + command_zfs_get_latest_snapshot)
    
    try:
        ssh = subprocess.Popen(command_get_latest_snapshot.split(' '),
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                    )
        result_latest_snapshot = ssh.stdout.read().decode().splitlines()[0]
    except subprocess.CalledProcessError as e:
        print("ERROR when obtaining latest snapshot:\n", e.output)
        sys.exit(1)
        
    return result_latest_snapshot.split("@")[1]
        

def pulldatasets(host, dataset, user, destination):
    sendoptions = "--raw"
    receiveoptions = ""
    command_ssh_connection = f"ssh {user}@{host}"
   
    result_latest_snapshot = get_latest_snapshot(host, dataset, user,)
   
    # Construct commands
    command_send = f"zfs send {sendoptions} {dataset}@{result_latest_snapshot}"
    command_receive = f"zfs receive {receiveoptions} {destination}/{host}/{dataset}"
    command_ssh_and_custom = command_ssh_connection +  ' ' + command_send
    
    print("DEBUG: " + command_ssh_and_custom)

    try:
        print(f"Initiating send from {host}")
        ssh = subprocess.Popen(
            command_ssh_and_custom.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )
       
        print("DEBUG: " + command_receive)
        print(f"Receiving ZFS stream from {host}")
        local = subprocess.Popen(command_receive.split(' '),
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=ssh.stdout
                    )
        
        stout, stderr = local.communicate()
        
        print('Result of receive ZFS stream')
        print(stout.decode())
        print(stderr.decode())
        
    except subprocess.CalledProcessError as e:
        print("ERROR: Backup failed.\n", e.output)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Push or pull ZFS backups from a remote host')
    parser.add_argument('--host', help='Remote host')
    parser.add_argument('--datasets', nargs='+', help='Source datasets')
    parser.add_argument('--user', default=DEFAULT_user, help='Remote SSH user')
    parser.add_argument('--destination', default=DEFAULT_destination, help='Local dataset to receive backups (default: %(default)s)')

    args = parser.parse_args()

    if not args.user or not args.host or not args.datasets:
        print("Usage: zfs-pull-backups --user <user> --host <host> --datasets-source <space-seperated list> [--datasets-destination <destination>]", file=sys.stderr)
        sys.exit(1)

    preflight(args.host, args.datasets, args.user, args.destination)
