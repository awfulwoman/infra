# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal home infrastructure management repository using Infrastructure-as-Code. Everything here controls actual home infrastructure - servers, networking, IoT devices, and containerized applications.

**Key technologies**: Ansible (primary), Terraform (Run from within Ansible), ESPHome (embedded devices), Docker Compose (web-based applications and services)

## Common Commands

```bash
# Install Ansible Galaxy dependencies
ansible-galaxy install -r ansible/meta/requirements.yaml
```

Playbooks are arranged to be cascading:

```bash
# Run all Core playbooks
ansible-playbook ansible/playbooks/core.yaml

# Run all Core bare-metal playbooks
ansible-playbook ansible/playbooks/baremetal/core.yaml

# Run only the Core host-storage playbook
ansible-playbook ansible/playbooks/baremetal/host-storage/core.yaml
```

## Architecture

### Ansible (`ansible/`)

The primary configuration management tool. Structure:

- **`inventory/`**: Host definitions (`hosts.yaml`), `host_vars/`, `group_vars/`
- **`roles/`**: ~97 roles following naming conventions:
  - `bootstrap-*`: Roles to setup essential configurations of a host type (personal machines, Ubuntu servers)
  - `composition-*`: Docker Compose applications (roughly 39 roles - homeassistant, gitea, jellyfin, etc.)
  - `system-*`: System configurations (docker, zfs, security)
  - `server-*`: The server half of client-server pairs
  - `client-*`: The client half of client-server pairs
- **`playbooks/`**: Organized by target type (`baremetal/`, `clusters/`, `virtual/`, `personal/`, `utility/`)
  - Each target has several playbook files:
    - `core.yaml`: This configures the entire host, including Docker Compose
    - `compositions.yaml`: This configures just Docker Compose applications
    - `dev.yaml`: For adhoc and experimental tasks
- **`plugins/filters/`**: Custom Ansible filter plugins

**Ansible configuration** (`ansible.cfg`):

- Inventory: `./ansible/inventory/hosts.yaml`
- Galaxy roles: `/opt/ansible/galaxy/roles`
- Galaxy collections: `/opt/ansible/galaxy/collections`
- Vault identity: `beanpod`

### Flux/Kubernetes (`flux/`)

GitOps-based cluster management for the "workloads" cluster:

- **`clusters/`**: Cluster configurations
- **`infrastructure/`**: Core K8s infrastructure (storage, DNS, sealed-secrets, longhorn, cert-manager)
- **`apps/`**: Application deployments

The Flux/Kubernetes cluster (`flux/`) is experimental, and should be ignored for now.

### ESPHome (`esphome/`)

Configuration for embedded devices. Uses a package-based system where device configs import from `esphome/packages/` (esphome.yaml, wifi.yaml, logger.yaml, ota.yaml, api.yaml, time.yaml).

Devices must define substitutions for secrets since secrets can't be used inside imported code.

### Terraform

Located in various places for QEMU/libvirt virtual machine provisioning.

## Key Patterns

- **Credentials**: Stored encrypted in repo using Ansible Vault
- **Networking**: Everything accessed via Tailscale
- **Docker Compose apps**: Templated with Jinja2 (`.yaml.j2` files), deployed via `composition-*` roles

## Session Logging

A custom Claude agent (`session-logger`) maintains `log.md` for continuity across work sessions. Use it when ending sessions or reaching significant milestones.
