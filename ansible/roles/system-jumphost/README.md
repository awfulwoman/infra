# system-jumphost

Configures a host as an Ansible jumphost/control plane.

## Requirements

- Depends on `ansible-core` role

## What it does

- Creates `/opt/ansible/` directory for Ansible operations
- Configures SSH client config (`~/.ssh/config`) with entries for all hosts
  in the `infra` inventory group
- Sets username to `awful` for all infrastructure hosts
- Disables strict host key checking for convenience (infra hosts accessed via Tailscale)

## Usage

Include this role in playbooks for hosts that need to run Ansible against infrastructure.
