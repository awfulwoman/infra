# Bootstrap Ubuntu Vagrant Wrapper

A variant of `bootstrap-ubuntu-server` tailored for Vagrant-managed Ubuntu VMs used as local development and testing environments. It runs the same core bootstrap steps but with a lighter package set (no restic, smartmontools, direnv, mosh, or Ubuntu Pro) and adds Vagrant-specific conveniences.

## Differences from bootstrap-ubuntu-server

- **No Tailscale** — Vagrant VMs are local-only and don't need to join the Tailscale network.
- **No automation-key-updater** — Not needed for ephemeral VMs.
- **SSH agent auto-start** — Adds a `keychain`-based SSH agent block to `.bashrc` so that keys loaded on first login persist across shells. Controlled by `bootstrap_ubuntu_ssh_agent_enable`.
- **SSH config generation** — Writes `~/.ssh/config` entries for all hosts in the `infra` inventory group with `StrictHostKeyChecking no` and `UserKnownHostsFile /dev/null`, making it easy to SSH between VMs without host key prompts. Controlled by `bootstrap_ubuntu_ssh_config_enable`.
- **Workspace auto-cd** — Optionally adds a `cd` line to `.bashrc` so the shell drops into a working directory on login (`bootstrap_ubuntu_workspace_path`).
- **Debug output** — Prints hostname, FQDN, Ansible connection address, and default IP at the start of the run to aid troubleshooting in Vagrant environments where these can differ.

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
