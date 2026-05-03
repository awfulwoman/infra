# Ansible - Meta

Handles external dependencies for Ansible.

## Installation

```bash
ansible-galaxy install -r meta/requirements.yaml
```

## Upgrading

Upgrade Collections.

```bash
ansible-galaxy collection install -r meta/requirements.yaml --upgrade
```

Why can you upgrade Collections with `--upgrade` but you can't do the same for Roles? No freaking idea. Sort it out, Ansible. Inconsistent command structures are one of the reasons people dunk on you.
