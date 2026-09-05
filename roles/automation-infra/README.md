# automation-infra

This role automates regular runs of infrastructure playbooks through a
systemd timer.

## Purpose

This role configures a systemd service and timer to run a
specified Ansible playbook on a schedule. It keeps infrastructure
configurations enforced without manual work.

## Requirements

- Ansible installed on the target host
- Ansible vault password file configured
- SSH keys configured for accessing remote hosts in the inventory
- Repository cloned to the configured path

## How It Works

The role does five things:

1. Checks that Ansible is installed. It fails if Ansible is not present.
2. Checks that the playbook and inventory paths exist.
3. Creates a systemd service that runs the specified playbook.
4. Creates a systemd timer to schedule regular runs.
5. Enables and starts the timer.

The host that runs this automation must have SSH access to
all target hosts named in the playbook.

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
automation_infra_playbook: "{{ ansible_infra_dir }}/playbooks/custom.yaml"
automation_infra_schedule: "hourly"
```

## Notes

- The service runs as root. System configuration needs this.
- The systemd timer uses a random delay of up to 10 minutes, to
  stop a thundering herd.
- Each playbook run has a 1-hour timeout.
- Logs go to the systemd journal.

## Checking Status

```bash
# Check timer status
systemctl status automation-infra.timer

# Check service status
systemctl status automation-infra.service

# View recent logs
journalctl -u automation-infra.service -n 50
```
