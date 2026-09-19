# automation-infra

This role runs a list of infrastructure playbooks on a schedule. It uses a
systemd timer on Linux and a launchd daemon on macOS.

## Requirements

- Ansible installed on the target host (the `ansible-core` role). On Linux
  this is the system install from the Ansible PPA; on macOS, Homebrew.
- The Ansible vault password file
- An SSH deploy key that can clone `automation_infra_repo_url`
- SSH access from the host to every target of the listed playbooks
- The repository checked out at `ansible_infra_dir` (`system-repos`)

## How It Works

The role deploys a run script to `automation_infra_script_path`. Each run:

1. Clones `automation_infra_repo_url` into a temporary directory.
2. Installs the Galaxy dependencies from the clone's
   `meta/requirements.yaml`.
3. Runs each playbook in `automation_infra_playbooks` from the clone.
4. Deletes the clone.

The run fails if the Galaxy install or any playbook fails. A failed playbook
does not stop the playbooks after it.

The role checks that each listed playbook and the inventory exist in
`ansible_infra_dir` before it installs the schedule.

## Configuration

Variables (see `defaults/main.yaml`):

- `automation_infra_playbooks`: Playbooks to run, relative to `playbooks/`
  (default: `[]`, which runs only the Galaxy install)
- `automation_infra_schedule`: `hourly`, `daily` or `weekly` (default:
  `daily`)
- `automation_infra_repo_url`: Repository to clone for each run
- `automation_infra_vault_password_file`: Path to the vault password file
- `automation_infra_service_name`: systemd unit name (default:
  `automation-infra`)
- `automation_infra_plist_label`: launchd label (default:
  `local.automation-infra`)

## Example Usage

```yaml
automation_infra_playbooks:
  - hosts/router-4gb-bertha/core.yaml
automation_infra_schedule: "daily"
```

## Notes

- The service runs as `ansible_user`, not root. Tasks that need root use
  `become` with the vault password.
- On Linux, the timer adds a random delay of up to 10 minutes and runs a
  missed schedule at the next boot. Each run has a 1-hour timeout.
- On macOS, runs start at 00:00 with no random delay.

## Checking Status

```bash
# Linux
systemctl list-timers automation-infra.timer
journalctl -u automation-infra.service -n 50

# macOS
sudo launchctl print system/local.automation-infra
tail -n 50 /usr/local/var/log/automation-infra.log
```
