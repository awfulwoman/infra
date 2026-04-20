# System Sleep Until

Deploys a script and optional cron job that suspends a Linux host until a specified wake-up time using `rtcwake`.

The core use case is energy-efficient home servers that should be offline overnight but wake up automatically in the morning. The script handles the edge case where the requested wake time has already passed today by scheduling wake-up for the same time tomorrow.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `sleepuntil_active` | `false` | Enable the role. When `false`, the script and cron job are removed. |
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

- `sleepuntil_active: false` is the safe default — setting it to `false` actively cleans up the script and cron entry, making the role easy to deactivate without leaving behind stale configuration.
- The role grants passwordless sudo for `rtcwake` and `killall` to the Ansible user, since these commands are needed to suspend the host without an interactive password prompt.
- The script kills any already-running `rtcwake` instance before suspending, preventing conflicts if the cron fires while a manual invocation is pending.
- Pairs naturally with `system-wakeonlan` — WoL handles waking the host remotely while this role handles scheduled automatic wake.
