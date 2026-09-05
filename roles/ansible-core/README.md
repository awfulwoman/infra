# Ansible Core

This role installs Ansible and its dependencies on a host. It then makes sure that the directory structure for local playbook runs exists. It supports macOS, through Homebrew, and Ubuntu/Debian, through the official Ansible PPA.

## Platform Behavior

- **macOS:** Installs `ansible` and `ansible-lint` through Homebrew.
- **Ubuntu/Debian:** Adds the `ppa:ansible/ansible` repository. Then it installs `ansible` and `ansible-lint` through apt.

After installation, the role does two things:

1. It runs `ansible-galaxy install -r meta/requirements.yaml` to install Galaxy dependencies, when `ansible_infra_dir` is defined.
2. It creates the directories referenced by `ansible_path`, `ansible_log_path`, and `ansible_roles_path`. This gives later Ansible runs a consistent working environment.

## Variables

These variables are expected in `host_vars` or `group_vars` as part of the Ansible automation setup for a host:

| Variable | Description |
|---|---|
| `ansible_infra_dir` | Path to the cloned infra repo on the host; used to locate `meta/requirements.yaml` |
| `ansible_path` | Base working directory for Ansible (e.g. `/opt/ansible`) |
| `ansible_log_path` | Path where Ansible logs are written |
| `ansible_collections_path` | Path for installed Galaxy collections |
| `ansible_roles_path` | Colon-separated path(s) for installed Galaxy roles |
