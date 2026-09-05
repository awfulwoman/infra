# automation-key-updater

This role fetches SSH public keys from a GitHub user account and keeps them updated through cron.

## Purpose

This role gives disaster recovery for SSH access. It syncs SSH keys from GitHub on a schedule. If you lose local SSH keys, you can still access machines, as long as you can push new keys to your GitHub account.

## Features

- Fetches public keys from `https://github.com/<username>.keys`.
- Runs immediately on deployment.
- Schedules daily updates through cron, at 3:15 AM by default.
- Uses markers to manage GitHub keys safely, without changes to other authorized_keys entries.

## Configuration

```yaml
# GitHub username to fetch keys from (currently fetched from GitHub)
automation_key_updater_username: "awfulwoman"

# Target user account
automation_key_updater_target_user: "{{ ansible_user }}"

# Cron schedule
automation_key_updater_cron_hour: "3"
automation_key_updater_cron_minute: "15"
```

## Implementation

- Installs the script to `/usr/local/bin/update-automation-keys`.
- Creates a cron job that runs as root.
- Marks keys with `# BEGIN/END GITHUB KEYS` comments.
- Replaces the previous GitHub keys on each run.

## Related

- GitHub Issue: #157
- Used by: `bootstrap-ubuntu-server`
