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

Why can you upgrade collections with `--upgrade`, but not roles? I have no idea. Ansible needs to fix this. Inconsistent command structures are one reason people criticize Ansible.
