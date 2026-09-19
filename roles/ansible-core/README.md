# Ansible Core

This role installs Ansible and its dependencies on a host. It then makes sure that the directory structure for local playbook runs exists. It supports macOS, through Homebrew, and Ubuntu/Debian, through the official Ansible PPA.

## Platform Behavior

- **macOS:** Installs `ansible` and `ansible-lint` through Homebrew.
- **Ubuntu/Debian:** Adds the `ppa:ansible/ansible` repository. Then it installs `ansible` and `ansible-lint` through apt.

After installation, the role does two things, in this order:

1. It creates the directories referenced by `ansible_path`, `ansible_log_path`, `ansible_collections_path`, and the absolute entries of `ansible_roles_path`. This gives later Ansible runs a consistent working environment.
2. It copies this repo's `meta/requirements.yaml` from the controller to `ansible_path`, then runs `ansible-galaxy install` against it into `ansible_roles_path` and `ansible_collections_path`. The host needs no checkout of this repo.

The order matters. `ansible-galaxy` writes straight into the roles and collections paths, so on a fresh host it fails unless those directories already exist and the connecting user can write to them. The directories are created with `become`, because `ansible_path` is usually under `/opt`, and are then owned by `ansible_user`, which is the account that runs `ansible-galaxy`.

The role does not create the file named by `ansible_vault_password_file`. Placing it remains a manual, out-of-band step.

## Variables

These variables are expected in `host_vars` or `group_vars` as part of the Ansible automation setup for a host:

| Variable | Description |
|---|---|
| `ansible_path` | Base working directory for Ansible (e.g. `/opt/ansible`) |
| `ansible_log_path` | Path where Ansible logs are written |
| `ansible_collections_path` | Path for installed Galaxy collections |
| `ansible_roles_path` | Colon-separated path(s) for installed Galaxy roles |
