# system-github-ssh-keys

TODO: remane to `automation-key-updater`

Fetches SSH public keys from a GitHub user account and keeps them updated via cron.

## Purpose

Provides disaster recovery for SSH access by automatically synchronizing SSH
keys from GitHub. If you lose local SSH keys, you can still access machines as
long as you can push new keys to your GitHub account.

## Features

- Fetches public keys from `https://github.com/<username>.keys`
- Runs immediately on deployment
- Schedules daily updates via cron (default: 3:15 AM)
- Uses markers to safely manage GitHub keys without affecting other
  authorized_keys entries

## Configuration

```yaml
# GitHub username to fetch keys from
system_github_ssh_keys_username: "awfulwoman"

# Target user account
system_github_ssh_keys_target_user: "{{ ansible_user }}"

# Cron schedule
system_github_ssh_keys_cron_hour: "3"
system_github_ssh_keys_cron_minute: "15"
```

## Implementation

- Installs script to `/usr/local/bin/update-github-ssh-keys`
- Creates cron job running as root
- Keys are marked with `# BEGIN/END GITHUB KEYS` comments
- Previous GitHub keys are replaced on each run

## Related

- GitHub Issue: #157
- Used by: `bootstrap-ubuntu-server`
