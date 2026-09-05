# Bootstrap Ubuntu Vagrant Wrapper

This role is a variant of `bootstrap-ubuntu-server` for Vagrant-managed Ubuntu VMs used as local development and testing environments. It runs the same core bootstrap steps, but with a lighter package set (no restic, smartmontools, direnv, mosh, or Ubuntu Pro), and adds Vagrant-specific conveniences.

## Differences from bootstrap-ubuntu-server

- **No Tailscale** — Vagrant VMs are local-only and do not need to join the Tailscale network.
- **No automation-key-updater** — Ephemeral VMs do not need this.
- **SSH agent auto-start** — Adds a `keychain`-based SSH agent block to `.bashrc`, so that keys loaded on first login persist across shells. `bootstrap_ubuntu_ssh_agent_enable` controls this.
- **SSH config generation** — Writes `~/.ssh/config` entries for all hosts in the `infra` inventory group, with `StrictHostKeyChecking no` and `UserKnownHostsFile /dev/null`. This lets you SSH between VMs without host key prompts. `bootstrap_ubuntu_ssh_config_enable` controls this.
- **Workspace auto-cd** — Can add a `cd` line to `.bashrc`, so the shell moves into a working directory on login (`bootstrap_ubuntu_workspace_path`).
- **Debug output** — Prints the hostname, FQDN, Ansible connection address, and default IP at the start of the run. This helps with troubleshooting in Vagrant environments, where these values can differ.

## Variables

| Variable | Default | Description |
|---|---|---|
| `bootstrap_ubuntu_timezone` | `Europe/Berlin` | System timezone |
| `bootstrap_ubuntu_apt_packages` | *(see defaults)* | List of apt packages to install |
| `bootstrap_ubuntu_ssh_agent_enable` | `true` | Add keychain-based SSH agent to `.bashrc` |
| `bootstrap_ubuntu_ssh_key_path` | `~/.ssh/id_ed25519` | SSH key loaded by keychain |
| `bootstrap_ubuntu_ssh_config_enable` | `true` | Write SSH config entries for infra hosts |
| `bootstrap_ubuntu_ssh_config_infra_group` | `infra` | Inventory group to generate SSH config for |
| `bootstrap_ubuntu_ssh_config_user` | `{{ vault_server_username }}` | Username written into generated SSH config |
| `bootstrap_ubuntu_ssh_config_strict_host_key_checking` | `false` | Whether to enable strict host key checking |
| `bootstrap_ubuntu_ssh_config_user_known_hosts_file` | `/dev/null` | Known hosts file for generated entries |
| `bootstrap_ubuntu_workspace_path` | `""` | If set, auto-cd into this path on login |
