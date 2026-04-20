# System Security

Hardens Ubuntu server security by configuring unattended-upgrades, SSH, sudo access, and fail2ban in a single role.

This role is applied to all Ubuntu bare-metal hosts as part of the bootstrap process. It is intentionally opinionated — password authentication and root login are disabled by default, and automatic reboots are scheduled at 03:00 for security updates.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `security_autoupdate_enabled` | `true` | Enable unattended-upgrades |
| `security_autoupdate_additional_origins` | (Docker, Tailscale, HashiCorp, etc.) | Third-party apt origins to include in auto-updates |
| `security_autoupdate_reboot` | `true` | Allow unattended-upgrades to reboot the host |
| `security_autoupdate_reboot_time` | `03:00` | Time to reboot after applying updates |
| `security_autoupdate_mail_to` | `unattended@<domain>` | Address to email on upgrade errors |
| `security_sudoers_passwordless` | `["{{ vault_server_username }}"]` | Users granted passwordless sudo |
| `security_sudoers_passworded` | `[]` | Users granted passworded sudo |
| `security_ssh_port` | `22` | SSH listen port |
| `security_ssh_password_authentication` | `false` | Allow SSH password auth |
| `security_ssh_permit_root_login` | `false` | Allow root SSH login |
| `security_ssh_allowed_users` | `[]` | Restrict SSH to specific users (empty = no restriction) |
| `security_ssh_allowed_groups` | `[]` | Restrict SSH to specific groups (empty = no restriction) |
| `security_fail2ban_custom_configuration_template` | `jail.local.j2` | Jinja2 template for fail2ban jail config |

## Design Notes

- The `50unattended-upgrades` template is Ubuntu Pro-aware: if the host is attached to Ubuntu Pro (detected at runtime via `pro status`), ESM origins are automatically added to the allowed origins list. This requires `system-ubuntupro` to run before this role if ESM updates are desired.
- A legacy file `/etc/apt/apt.conf.d/90-ansible-unattended-upgrades` is explicitly removed to clean up after an older role naming convention.
- SSH config changes are validated with `sshd -T` before being applied, and trigger a handler to restart the SSH daemon.
- Sudo entries are validated with `visudo -cf` before writing.
