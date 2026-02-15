# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

## Your Communication as an Agent

- In all interactions and messages, be extremely concise and sacrifice
  grammar for the sake of conciseness.
- Don't be afraid to tell the user when an idea is bad.
- Don't be afraid to admit you are wrong.
- The last line of every response must make sense when spoken aloud via
  text-to-speech. Avoid ending with code blocks, file paths, or technical
  symbols.

## Repository Overview

This is a personal home infrastructure management repository using
Infrastructure-as-Code. Everything here controls actual home infrastructure -
servers, networking, IoT devices, and containerized applications.

**Key technologies**: Ansible (primary), Terraform (Run from within
Ansible), ESPHome (embedded devices), Docker Compose (web-based
applications and services)

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

## Github

- Your primary method of interacting with GitHub should be the GitHub
  CLI tool, `gh`.
- If the GitHub CLI tool is not installed, alert the user.

## Architecture

### Ansible (`ansible/`)

The primary configuration management tool. Structure:

- **`inventory/`**: Host definitions (`hosts.yaml`), `host_vars/`,
  `group_vars/`
- **`roles/`**: ~93 roles following naming conventions:
  - `bootstrap-*`: Essential configurations for a host type (personal
    machines, Ubuntu servers)
  - `composition-*`: Docker Compose applications (~39 roles -
    homeassistant, gitea, jellyfin, etc.)
  - `backups-zfs-*`: ZFS backup infrastructure (client, server, offsite)
  - `system-*`: System configurations (docker, zfs, zfs-policy, security)
  - `server-*`: Server half of client-server pairs (nfs, nut)
  - `client-*`: Client half of client-server pairs (nfs, nut)
  - `virtual-*`: Virtualisation roles (qemu-host, qemu-guest, hetzner)
  - `hardware-*`: Hardware-specific configs (raspberry-pi, zigbee-conbee,
    rtl-433)
  - `monitoring-*`: Monitoring integrations (healthchecksio, linux2mqtt)
  - `network-*`: Network configuration
    - `network-netplan`: Netplan-based network configuration for primary
      interface (supports static IP and DHCP)
    - `network-register-subdomain`: DNS subdomain registration
    - `network-ip-address-forwarding`: IPv4 forwarding via sysctl
  - `infra-*`: Infrastructure resources provisioned via Terraform
- **`playbooks/`**: Organized by target type (`baremetal/`, `clusters/`,
  `virtual/`, `personal/`, `utility/`)
  - Each target has several playbook files:
    - `core.yaml`: This configures the entire host, including Docker Compose
    - `compositions.yaml`: This configures just Docker Compose applications
    - `dev.yaml`: For adhoc and experimental tasks
- **`plugins/filters/`**: Custom Ansible filter plugins (e.g.,
  `zfs_datasets.py` for processing declarative `zfs:` structures)

**Ansible configuration** (`ansible.cfg`):

- Inventory: `./ansible/inventory/hosts.yaml`
- Galaxy roles: `/opt/ansible/galaxy/roles`
- Galaxy collections: `/opt/ansible/galaxy/collections`
- Vault identity: `beanpod`

### Flux/Kubernetes (`flux/`)

GitOps-based cluster management for the "workloads" cluster:

- **`clusters/`**: Cluster configurations
- **`infrastructure/`**: Core K8s infrastructure (storage, DNS,
  sealed-secrets, longhorn, cert-manager)
- **`apps/`**: Application deployments

The Flux/Kubernetes cluster (`flux/`) is experimental, and should be
ignored for now.

### ESPHome (`esphome/`)

Configuration for embedded devices. Uses a package-based system where
device configs import from `esphome/packages/` (esphome.yaml, wifi.yaml,
logger.yaml, ota.yaml, api.yaml, time.yaml).

Devices must define substitutions for secrets since secrets can't be used
inside imported code.

### Terraform

Located in `ansible/roles/infra-*/templates/` for provisioning infrastructure:

- **Local**: QEMU/libvirt virtual machines
- **Public**: Hetzner Cloud (servers, floating IPs, DNS, firewalls)

Templates are split by provider (`digitalocean.tf`, `hetzner.tf`) and
rendered by Ansible during playbook runs.

### Scripts (`scripts/`)

Utility shell scripts for common operations (e.g., `flush-dns.sh`).

### Documentation (`docs/`)

Project documentation including architecture guides, runbooks, and reference
material.

## Key Patterns

- **Credentials**: Stored encrypted in repo using Ansible Vault
- **Networking**: Everything accessed via Tailscale
- **Docker Compose apps**: Templated with Jinja2 (`.yaml.j2` files),
  deployed via `composition-*` roles

## Plans

- Whenever a plan is requested, ALWAYS save a copy of it as a markdown file
  in plans/.
- When you are implementing a plan, always ask if the user wants to create
  a pull request, rather than automatically committing to main.

## MCP Servers

- Always use Context7 MCP when I need library/API documentation, code
  generation, setup or configuration steps without me having to explicitly
  ask.
