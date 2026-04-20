# Ansible Pull

Configures a host to self-provision via `ansible-pull`, pulling the infrastructure repo and running its own playbook on a schedule. This is how hosts stay up to date without needing a remote controller to push changes to them.

## What it does

1. Writes the Ansible vault password to `{{ ansiblepull_workdir }}/.vaultpassword`.
2. Creates the working directory structure: `{{ ansiblepull_workdir }}/`, `galaxy/roles/`, `galaxy/collections/`, and the repo clone path.
3. Clones the infra repo and, on first run (gated by a lockfile), installs all Galaxy roles and collections — with a long timeout because `ansible-galaxy` is slow.
4. Sets up cron jobs to run `ansible-galaxy` role and collection installs daily at 05:15 and 05:30.
5. Deploys pull scripts from templates and sets up a cron job to run `ansible-pull-full.sh` on the configured schedule.
6. Optionally installs a systemd service (`ansible-pull-after-wake.service`) that re-runs the pull script after the host wakes from sleep or hibernate.

## Pull Scripts

Two scripts are deployed to `{{ ansiblepull_workdir }}/scripts/`:

- **`ansible-pull-full.sh`** — Pulls the latest git state and runs `playbooks/{{ host_type }}/{{ host_name }}/{{ ansiblepull_playbook }}.yaml`. Used by the regular cron and wake-from-sleep service.
- **`ansible-pull-compositions.sh`** — Runs only the `compositions.yaml` playbook without a git pull. Useful for quickly redeploying Docker Compose services.

Both scripts use `flock`-based locking to prevent concurrent runs.

## First-Run Caveat

The vault password and SSH credentials needed to clone a private repo must be present before `ansible-pull` can work autonomously. For a freshly imaged host this means the first run must be pushed from a remote controller — after that, the host is self-sufficient.

## Variables

| Variable | Default | Description |
|---|---|---|
| `ansiblepull_cron_minute` | `"0"` | Minute field for the pull cron |
| `ansiblepull_cron_hour` | `"5,17"` | Hour field for the pull cron (runs at 05:00 and 17:00) |
| `ansiblepull_workdir` | `{{ ansible_path }}` | Base directory for all Ansible pull state |
| `ansiblepull_script_name` | `ansible-pull-full.sh` | Script invoked by cron and the wake service |
| `ansiblepull_lockfile_name` | `ansible-pull.lock` | Flock lockfile name |
| `ansiblepull_initial_installer_lockfile_name` | `.ansible-galaxy-installed.lock` | Prevents Galaxy re-install on every run |
| `ansiblepull_install_pull_cron` | `true` | Whether to install the pull cron job |
| `ansiblepull_repo_url` | `https://github.com/awfulwoman/infra` | Repo URL passed to `ansible-pull` |
| `ansiblepull_repo_path` | `{{ ansible_infra_dir }}` | Local path where the repo is cloned |
| `ansiblepull_playbook` | `core` | Playbook name (without extension) to run |
| `ansiblepull_run_after_wake` | `false` | Install the systemd wake-from-sleep service |

## Dependencies

Depends on `ansible-core` to ensure Ansible itself is installed before this role runs.
