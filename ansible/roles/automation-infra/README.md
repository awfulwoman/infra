# automation-infra

Automates regular execution of infrastructure playbooks via systemd
timer.

## Purpose

This role configures a systemd service and timer to regularly run any
specified Ansible playbook. Ensures infrastructure configurations are
continuously enforced without manual intervention.

## Requirements

- Ansible installed on the target host
- Ansible vault password file configured
- SSH keys configured for accessing remote hosts in the inventory
- Repository cloned to the configured path

## How It Works

The role:

1. Checks that Ansible is installed (fails if not present)
2. Verifies playbook and inventory paths exist
3. Creates a systemd service that runs the specified playbook
4. Creates a systemd timer to schedule regular executions
5. Enables and starts the timer

The host running this automation must have appropriate SSH access to
all target hosts referenced in the playbook.

## Configuration

Variables (see `defaults/main.yaml`):

- `automation_infra_schedule`: How often to run (hourly/daily/weekly,
  default: daily)
- `automation_infra_playbook`: Path to the playbook to run
- `automation_infra_inventory`: Path to the inventory file
- `automation_infra_vault_password_file`: Path to vault password file
- `automation_infra_service_name`: systemd service/timer name
  (default: automation-infra)

## Example Usage

Override variables in host_vars or group_vars to customize:

```yaml
automation_infra_playbook: "{{ home_repo_dir }}/ansible/playbooks/custom.yaml"
automation_infra_schedule: "hourly"
```

## Notes

- Service runs as root (required for system configuration)
- Uses systemd timer with randomized delay (up to 10 minutes) to
  prevent thundering herd
- Playbook execution has 1-hour timeout
- Logs are sent to systemd journal

## Checking Status

```bash
# Check timer status
systemctl status automation-infra.timer

# Check service status
systemctl status automation-infra.service

# View recent logs
journalctl -u automation-infra.service -n 50
```
