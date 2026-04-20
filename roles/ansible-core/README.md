# Ansible Core

Installs Ansible and its dependencies on a host, then ensures the required directory structure exists for local playbook execution. Handles both macOS (via Homebrew) and Ubuntu/Debian (via the official Ansible PPA).

## Platform Behaviour

- **macOS:** Installs `ansible` and `ansible-lint` via Homebrew.
- **Ubuntu/Debian:** Adds the `ppa:ansible/ansible` repository, then installs `ansible` and `ansible-lint` via apt.

After installation, the role:

1. Runs `ansible-galaxy install -r meta/requirements.yaml` to ensure Galaxy dependencies are present (when `ansible_infra_dir` is defined).
2. Creates the directories referenced by `ansible_path`, `ansible_log_path`, and `ansible_roles_path` so subsequent Ansible runs have a consistent working environment.

## Variables

These variables are expected in `host_vars` or `group_vars` as part of the Ansible automation setup for a host:

| Variable | Description |
|---|---|
| `ansible_infra_dir` | Path to the cloned infra repo on the host; used to locate `meta/requirements.yaml` |
| `ansible_path` | Base working directory for Ansible (e.g. `/opt/ansible`) |
| `ansible_log_path` | Path where Ansible logs are written |
| `ansible_collections_path` | Path for installed Galaxy collections |
| `ansible_roles_path` | Colon-separated path(s) for installed Galaxy roles |
