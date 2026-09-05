# Bootstrap Ubuntu Server

This role does the full initial bootstrap of an Ubuntu server. It is the primary bootstrap role for all baremetal Ubuntu hosts. It installs core packages, configures the locale and timezone, sets the hostname, joins Tailscale, and wires up supporting roles for security, monitoring, and tooling.

## What it does

1. **Packages** — Installs a standard set of apt packages (curl, git, tmux, vim, restic, smartmontools, mosh, python3, direnv, and others).
2. **Shell** — Sets bash as the default shell and hooks direnv into `.bashrc` for both `root` and the Ansible user.
3. **Locale and timezone** — Configures the locale (`config_system_locale`), language (`config_system_language`), and timezone (default: `Europe/Berlin`). It uses `localectl` and applies changes only when the current state differs.
4. **Hostname** — Sets the system hostname and makes sure that `127.0.1.1` resolves to `host_name` in `/etc/hosts`.
5. **PPAs** — Adds `ppa:m-grant-prg/utils` and `ppa:tomtomtom/yt-dlp`.
6. **Tailscale** — Checks the current connection state before it runs, so it does not re-authenticate an already-connected node. It generates an auth key through `network-tailscale-authkey` when needed. If `tailscale_exit_node: true` is set in host_vars, the role brings up the node with `--advertise-exit-node`.
7. **Included roles** — `automation-key-updater`, `system-pipx`, `system-environment`, `system-ubuntupro`, `system-security` (fail2ban disabled), `system-motd`, `system-git`.
8. **sudo rsync** — Grants the Ansible user passwordless `sudo rsync` to support ZFS backup transfers.

## Variables

| Variable | Default | Description |
|---|---|---|
| `bootstrap_ubuntu_timezone` | `Europe/Berlin` | System timezone |
| `bootstrap_ubuntu_apt_packages` | *(see defaults)* | List of apt packages to install |

Additional variables consumed from inventory:

| Variable | Description |
|---|---|
| `host_name` | Sets the system hostname |
| `config_system_locale` | Locale string (e.g. `en_GB.UTF-8`) |
| `config_system_language` | Language string (e.g. `en_GB:en`) |
| `tailscale_exit_node` | If `true`, advertises this node as a Tailscale exit node |
