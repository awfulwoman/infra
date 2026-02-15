# automation-zfs-backup-playbook

Automates regular execution of the ZFS backup infrastructure playbook
via systemd timer.

## Purpose

This role configures a systemd service and timer to regularly run the
ZFS backup infrastructure playbook
(`ansible/playbooks/zfs/backup-infra.yaml`). This ensures backup
configurations are continuously enforced across all ZFS backup clients
and servers.

## Requirements

- Ansible installed on the target host
- Ansible vault password file configured
- SSH keys configured for accessing remote hosts in the inventory
- Repository cloned to the configured path

## How It Works

The role:
1. Checks that Ansible is installed (fails if not present)
2. Verifies playbook and inventory paths exist
3. Creates a systemd service that runs the backup playbook
4. Creates a systemd timer to schedule regular executions
5. Enables and starts the timer

The playbook targets multiple host groups (`zfs-backup-clients`,
`zfs-backup-servers`, etc.), so the host running this automation must
have appropriate SSH access to all target hosts.

## Configuration

Variables (see `defaults/main.yaml`):

- `zfs_backup_playbook_schedule`: How often to run
  (hourly/daily/weekly, default: daily)
- `zfs_backup_playbook_path`: Path to the playbook
- `zfs_backup_playbook_inventory`: Path to the inventory file
- `zfs_backup_playbook_vault_password_file`: Path to vault password file

## Notes

- Service runs as root (required for ZFS operations and system configuration)
- Uses systemd timer with randomized delay (up to 10 minutes) to
  prevent thundering herd
- Playbook execution has 1-hour timeout
- Logs are sent to systemd journal

## Checking Status

```bash
# Check timer status
systemctl status zfs-backup-playbook.timer

# Check service status
systemctl status zfs-backup-playbook.service

# View recent logs
journalctl -u zfs-backup-playbook.service -n 50
```
