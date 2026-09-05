# System Sleep Until

Deploys a script and an optional cron job. The script uses `rtcwake` to suspend a Linux host until a set wake-up time.

The main use case is energy-efficient home servers. These servers stay offline overnight and wake up automatically in the morning. If the requested wake time already passed today, the script schedules wake-up for the same time tomorrow instead.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `sleepuntil_active` | `false` | Enable the role. When `false`, the role removes the script and cron job. |
| `sleepuntil_sleep_time` | `17:30` | Default wake-up time passed to `rtcwake` (overridden by `-T` flag) |
| `sleepuntil_suspend_mode` | `mem` | Suspend mode (see `man rtcwake`; `mem` = suspend-to-RAM) |
| `sleepuntil_script_path` | `/usr/local/bin/sleepuntil` | Path where the script is deployed |
| `sleepuntil_autosleep` | `false` | Enable automatic suspend via cron |
| `sleepuntil_autosleep_time_hour` | `1` | Hour for the auto-suspend cron entry |
| `sleepuntil_autosleep_time_minute` | `0` | Minute for the auto-suspend cron entry |
| `sleepuntil_wakeup_script` | `null` | Optional command to run after the host resumes |

## Usage

```bash
# Manually suspend until 08:30
sleepuntil -T 08:30
```

## Design Notes

- `sleepuntil_active: false` is the safe default. When set to `false`, the role cleans up the script and cron entry. This makes the role easy to deactivate. It leaves no stale configuration behind.
- The role grants passwordless sudo for `rtcwake` and `killall` to the Ansible user. The host needs these commands to suspend without an interactive password prompt.
- The script kills any `rtcwake` instance that already runs, before it suspends the host. This prevents conflicts if the cron job fires while a manual command is still pending.
- This role pairs naturally with `system-wakeonlan`. WoL wakes the host remotely, while this role handles scheduled automatic wake.
