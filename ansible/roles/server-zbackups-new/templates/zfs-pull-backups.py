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
    command_ssh_connection = f"ssh -tt {user}@{host}"
    command_zfs_get_latest_snapshot = f"zfs list -t snapshot -H -o name -S creation -r {dataset}"
    command_get_latest_snapshot = command_ssh_connection.split(' ') + command_zfs_get_latest_snapshot.split(' ')
    
    print(command_ssh_connection + ' ' + command_zfs_get_latest_snapshot)
    
    try:
        ssh = subprocess.Popen(command_get_latest_snapshot,
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
    command_receive = f"zfs receive {destination}/{host}/{dataset}"
    
    command_ssh_and_custom = command_ssh_connection +  ' ' + command_send
    # command_temp = "zfs list"
    
    print(command_ssh_and_custom)

    try:
        print('SSH connection and send')
        ssh = subprocess.run(
            command_ssh_and_custom.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
            )

        ssh_outs, ssh_errs = ssh.communicate()
        
        # print("ERRORS: \n" + ssh_errs.string())
        print(ssh_outs.decode())
        
        # print('Receive ZFS stream')
        # local = subprocess.Popen(command_receive.split(' '),
        #             shell=False,
        #             stdout=subprocess.PIPE,
        #             stderr=subprocess.PIPE,
        #             stdin=ssh.stdout
        #             )
        
        
        # stout, stderr = local.communicate()
        # # result = local.communicate(input=ssh_outs)
        # # p = subprocess.run(command_receive.split(' '), input=ssh_outs, capture_output=True, text=True)
        
        # print('Result of receive ZFS stream')
        # print(stout.decode())
        # print(stderr.decode())
        
    
    except subprocess.CalledProcessError as e:
        print("ERROR when conducting backup operation:\n", e.output)
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
