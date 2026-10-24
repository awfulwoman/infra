# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal home infrastructure management repository using Infrastructure-as-Code. Everything here controls actual home infrastructure - servers, networking, IoT devices, and containerized applications.

**Key technologies**: Ansible (primary), Terraform (Run from within Ansible), ESPHome (embedded devices), Docker Compose (web-based applications and services)

## Common Commands

```bash
# Install Ansible Galaxy dependencies
ansible-galaxy install -r meta/requirements.yaml
```

Playbooks are organised into two directories:

```bash
# Run a group playbook (e.g. bootstrap all Ubuntu servers)
ansible-playbook playbooks/groups/ubuntu/bootstrap.yaml

# Run a host-specific playbook
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml
```

Filter and lookup plugins (`plugins/filters/`, `plugins/lookup/`) with pure-Python logic are unit tested with pytest (install via `brew install pytest`, matching the Ansible/pre-commit Homebrew convention — no venv). Some tests need PyYAML, which isn't bundled with the pytest formula — install it into pytest's own venv, since it's isolated from the system/Ansible Python:

```bash
$(dirname "$(readlink -f "$(which pytest)")")/python -m pip install pyyaml
pytest
```

## Github

- Your primary method of interacting with GitHub should be the GitHub CLI tool, `gh`.
- If the GitHub CLI tool is not installed, alert the user.

## Architecture

### Ansible

The primary configuration management tool. Structure:

- **`inventory/`**: Host definitions (`hosts.yaml`), `host_vars/`, `group_vars/`
- **`roles/`**: ~93 roles following naming conventions:
  - `bootstrap-*`: Essential configurations for a host type (personal machines, Ubuntu servers)
  - `composition-*`: Docker Compose applications (~39 roles - homeassistant, gitea, jellyfin, etc.)
  - `backups-zfs-*`: ZFS backup infrastructure (client, server, offsite)
  - `backups-restic-offsite`: The Offsite copy, sent by the backup server with restic (ADR-0002)
  - `system-*`: System configurations (docker, zfs, zfs-policy, security)
  - `server-*`: Server half of client-server pairs (nfs, nut)
  - `client-*`: Client half of client-server pairs (nfs, nut)
  - `virtual-*`: Virtualisation roles (qemu-host, qemu-guest, hetzner)
  - `hardware-*`: Hardware-specific configs (raspberry-pi, zigbee-conbee, rtl-433)
  - `automation-*`: Scheduled automation on a host (e.g., `automation-key-updater` refreshes authorized SSH keys from GitHub). Scheduled playbook runs live in Semaphore on camina (`composition-semaphore`)
  - `monitoring-*`: Monitoring integrations (healthchecksio, linux2mqtt)
  - `network-*`: Network configuration
    - `network-netplan`: Netplan-based network configuration for primary interface (supports static IP and DHCP)
    - `network-register-subdomain`: DNS subdomain registration
    - `network-ip-address-forwarding`: IPv4 forwarding via sysctl
    - `network-tailscale-token`: Exchanges Tailscale OAuth credentials for an API bearer token
    - `network-tailscale-authkey`: Mints a one-time Tailscale enrolment key
    - `network-tailscale-address`: Pins a host's Tailscale IPv4 to the inventory's `host_tailscale_ipv4`
    - `network-tailscale-dns`: Sets the tailnet's global nameservers (run from bertha)
  - `infra-*`: Infrastructure resources provisioned via Terraform
- **`playbooks/`**: Split into `hosts/` (per-host) and `groups/` (per-group), plus `utility/`
  - Each host directory has several playbook files:
    - `core.yaml`: This configures the entire host, including Docker Compose
    - `compositions.yaml`: This configures just Docker Compose applications
    - `dev.yaml`: For adhoc and experimental tasks
- **`plugins/filters/`**: Custom Ansible filter plugins (e.g., `zfs_datasets.py` for processing declarative `zfs:` structures)

**Ansible configuration** (`ansible.cfg`):

- Inventory: `./inventory/hosts.yaml`
- Galaxy roles: `/opt/ansible/galaxy/roles` (Linux); macOS uses `{{ ansible_path }}/galaxy/roles`
- Galaxy collections: `/opt/ansible/galaxy/collections` (Linux); macOS uses `{{ ansible_path }}/galaxy/collections`
- Vault identity: `beanpod`
- `vault_password_file` is hardcoded to `/opt/ansible/.vaultpassword` — only correct on Linux; macOS hosts override via `ansible_vault_password_file` in host_vars

### Flux/Kubernetes (`flux/`)

GitOps-based cluster management for the "workloads" cluster:

- **`clusters/`**: Cluster configurations
- **`infrastructure/`**: Core K8s infrastructure (storage, DNS, sealed-secrets, longhorn, cert-manager)
- **`apps/`**: Application deployments

The Flux/Kubernetes cluster (`flux/`) is experimental, and should be ignored for now.

### ESPHome (`roles/composition-esphome/`)

Configuration for embedded devices, deployed by the `composition-esphome` role. Device configs (`templates/esphome/`) import shared boilerplate as local packages (`templates/esphome/packages/`: `esphome.yaml`, `wifi.yaml`, `logger.yaml`, `ota.yaml`, `api.yaml`, `time.yaml`).

Devices must define substitutions for secrets since secrets can't be used inside imported code.

### Terraform

Located in `roles/infra-*/templates/` for provisioning infrastructure:

- **Local**: QEMU/libvirt virtual machines
- **Public**: Hetzner Cloud (servers, floating IPs, DNS, firewalls)

Templates are split by provider (`digitalocean.tf`, `hetzner.tf`) and rendered by Ansible during playbook runs.

### Nightly Semaphore runs

Semaphore on camina (`composition-semaphore`) runs each scheduled host's `core.yaml` every night, between 01:30 and 05:00 Europe/Berlin. The list is `composition_semaphore_schedules` in `inventory/host_vars/minipc-8gb-camina/core.yaml`; a host that is not in it is only configured when someone runs its playbook by hand.

- **Runs deploy GitHub `main`, not the local checkout.** A change applied by hand and left unpushed is reverted by that night's run. Push it, or pause the host's schedule with `active: false` and deploy the semaphore composition.
- **Anything in a host's `core.yaml` happens unattended.** That includes Terraform on deedee (`infra-public-resources` applies whenever the plan differs) and certificate issuing on bertha (`infra-certbot`).
- **Certificates renew this way.** bertha issues them; each host's `client-cert-distribution` collects them on its own run. bertha runs after most hosts, so a renewed certificate reaches them the following night.
- **One run at a time.** A manual run started from Semaphore queues behind the nightly ones.
- **A heartbeat runs last** and pings healthchecks.io, which alerts if the night's runs stop happening.

### Scripts (`scripts/`)

Utility shell scripts for common operations (e.g., `flush-dns.sh`).

### Documentation (`docs/`)

Project documentation including architecture guides, runbooks, and reference material.

## Key Patterns

- **Credentials**: Stored encrypted in repo using Ansible Vault
- **Networking**: Everything accessed via Tailscale
- **Docker Compose apps**: Templated with Jinja2 (`.yaml.j2` files), deployed via `composition-*` roles

## Agent skills

### Issue tracker

Issues and PRDs live as GitHub issues, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
