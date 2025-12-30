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
        
def get_latest_snapshot(host, dataset, user, debug):
    command_ssh_connection = f"ssh {user}@{host}"
    command_zfs_get_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset}"
    command_get_latest_snapshot = command_ssh_connection + ' ' + command_zfs_get_latest_snapshot
    
    if debug:
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
        

def pulldatasets(host, dataset, user, destination, debug):
    sendoptions = "-R"
    receiveoptions = "-F"
    command_ssh_connection = f"ssh {user}@{host}"
   
    result_latest_snapshot = get_latest_snapshot(host, dataset, user, debug)
   
    # Construct commands
    command_send = f"zfs send {sendoptions} {dataset}@{result_latest_snapshot}"
    command_receive = f"zfs receive {receiveoptions} {destination}/{host}/{dataset}"
    command_ssh_and_custom = command_ssh_connection +  ' ' + command_send
    
    try:
        print(f"Initiating send from {host}")
        if debug:
            print("DEBUG: " + command_ssh_and_custom)
        remote = subprocess.run(
            command_ssh_and_custom.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
            )
        
        # print(remote)

        print(f"Receiving ZFS stream from {host}")
        print(f"Saving to {destination}/{host}/{dataset}")
        if debug:
            print("DEBUG: " + command_receive)
        receive_zfs = subprocess.run(command_receive.split(' '),
                            shell=False,
                            input=remote.stdout,
                            check=True
                            )
        
    except subprocess.CalledProcessError as e:
        print('#############################')
        print("ERROR: Backup failed.\n", e)
        print('#############################')
        print('')
    except Exception as e:
        print(e)
        sys.exit(1)

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
