# system-apple-reminders-server

This role installs [`apple-reminders-server`](https://github.com/awfulwoman/apple-reminders-server)
as a per-user LaunchAgent on this host. It is a small authorized REST API in
front of the real macOS Reminders app, through `EventKit`.
[`composition-gateway`](../composition-gateway) uses it as its reminders
backend, in place of the earlier Radicale/CalDAV backend.

## Requirements

- macOS only, and specifically **Malcolm**. Malcolm is the one host in this
  infra that stays logged into a GUI session at all times. EventKit's
  Reminders TCC permission needs this: a headless LaunchDaemon can never see
  the permission prompt or hold the grant.
- `uv`, installed through Homebrew. This role installs it if the host does not
  have it.

The role clones and updates the `awfulwoman/apple-reminders-server` repo
itself, over SSH, into `system_apple_reminders_server_repo_dir`. It no longer
depends on `system-repos` running first. Set
`system_apple_reminders_server_repo_update: false` to pin the checkout instead
of pulling on every deploy.

## Permission stability (code signing)

macOS TCC pins the Reminders grant to a **code identity**. The role does
**not** launch the server through `uv run`. That command spawns an
ad-hoc-signed interpreter. The cdhash of that interpreter changes on every
`uv sync` or Python upgrade, and this silently drops the grant. Instead the
role:

1. runs `uv sync` on the venv,
2. provisions a long-lived self-signed code-signing cert once
   (`scripts/setup_signing_cert.sh`, idempotent),
3. re-signs the interpreter with a fixed identifier on every deploy
   (`scripts/sign_runtime.sh`), and
4. launches the signed interpreter directly from the plist
   (`.venv/bin/python3 -m apple_reminders_server.main`).

TCC then matches on the cert and identifier, so the grant survives rebuilds.
To provision the cert **headlessly**, set
`system_apple_reminders_server_keychain_password` (from vault). This lets the
role run `security set-key-partition-list` without a prompt. You need this
only for the first provisioning run. If you leave it empty, run
`scripts/setup_signing_cert.sh` on Malcolm by hand once. It prompts for
keychain access: click "Always Allow". Later deploys sign fine without it.

## One manual step this role cannot automate

The **first** time the LaunchAgent starts, macOS shows a Reminders permission
dialog in Malcolm's GUI session. Someone must click "Allow" in person, once:

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-reminders-server | grep state
# if not "running", the permission dialog is likely waiting on-screen
```

Until that happens, the service starts, but every EventKit call blocks or
fails. Thanks to the stable signature, this approval happens only once. It
does not recur after `uv sync` or Python upgrades.

### If the prompt comes back after a restart

Seen on Malcolm 2026-09-11: a long-running instance (started before a re-sign)
held its grant in-process for weeks; the first restart after that re-signing
hit `tccd: Failed to match existing code requirement ... kTCCServiceReminders`
and a fresh prompt, even though `TCC.db` still had `auth_value=2` for the
interpreter path and `codesign --verify` passed. The stored code requirement
had drifted from the current signature. Recovery is the same one click:

```bash
# on Malcolm's screen: click Allow on the Reminders dialog, then
ssh malcolm 'launchctl kickstart -k gui/$(id -u)/com.awfulwoman.apple-reminders-server'
# if no dialog is visible (dismissed/timed out), force a fresh one:
ssh malcolm 'tccutil reset Reminders com.awfulwoman.apple-reminders-server' && \
ssh malcolm 'launchctl kickstart -k gui/$(id -u)/com.awfulwoman.apple-reminders-server'
```

The watchdog's restart cooldown (default 1800s) keeps a service stuck in this
state from re-prompting every interval, but it will still re-prompt once per
cooldown until someone clicks Allow. Boot the watchdog out while you wait:
`launchctl bootout gui/$(id -u)/com.awfulwoman.apple-reminders-server-watchdog`.

## Sidecar `meta.db` is authoritative state, not a cache

`meta.db` holds the caller-`id` -> EventKit-`calendarItemIdentifier` map, the
app-authoritative LWW timestamps, and deletion tombstones. None of it can be
rebuilt from EventKit. The service opens the file once at startup through a
plain `sqlite3.connect()` and never revalidates the handle, so if the file is
removed while the service runs it does **not** crash: every write fails with
`sqlite3.OperationalError: attempt to write a readonly database` (SQLite can't
create its journal against a path with no directory entry) and
`GET /reminders` returns 500. `KeepAlive` never fires because the process
never exits.

The role limits the damage:

- **Deploy-time backup.** Before it touches anything, the role copies `meta.db`
  to `meta.db.bak-<timestamp>` in the same directory and keeps the newest
  `system_apple_reminders_server_backup_keep` (7).
- **Marker file.** `~/.local/state/apple-reminders-server/DO-NOT-DELETE.txt`
  explains the above in place.
- **Watchdog** (below) turns "silently wedged until noticed" into "restarted
  within one interval, and alerted".

If you ever do need to remove or replace `meta.db`, restart the service in the
same breath:

```bash
launchctl kickstart -k gui/$(id -u)/com.awfulwoman.apple-reminders-server
```

## Watchdog

`system_apple_reminders_server_watchdog_enabled` (default true) deploys a second
LaunchAgent, `com.awfulwoman.apple-reminders-server-watchdog`, that runs
`~/.local/state/apple-reminders-server/reminders-watchdog.sh` every
`system_apple_reminders_server_watchdog_interval` seconds (300). It makes one
authenticated `GET /reminders`:

- 2xx -> ping the Healthchecks.io check (so a *missing* ping — watchdog dead,
  host down — also alerts).
- anything else -> ping `.../fail`, and `launchctl kickstart -k` the main
  agent **at most once per `..._watchdog_restart_cooldown` seconds** (1800).
  The cooldown matters because if the service is down because it is blocked on
  a Reminders TCC prompt (see below), every restart re-triggers that prompt on
  Malcolm's screen. A failure inside the cooldown only alerts.

The Healthchecks.io check is created by the role (needs
`vault_healthchecks_rw_apikey`, the same key `monitoring-healthchecksio` uses);
name is `system_apple_reminders_server_healthchecksio_name`. If the API is
unreachable at deploy time the watchdog still restarts the service, it just
can't alert — set `system_apple_reminders_server_healthchecksio_enabled: false`
to skip the check wiring entirely.

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_apple_reminders_server_repo_dir` | `system_repos_base_dir/awfulwoman/apple-reminders-server` | Repo checkout to run from |
| `system_apple_reminders_server_port` | `4100` | Local port the service listens on |
| `system_apple_reminders_server_bearer_tokens` | `vault_gateway_reminders_server_token` | Shared secret. Also set as `composition_gateway_reminders_server_bearer_token` |
| `system_apple_reminders_server_default_list` | `Reminders` | List (EKCalendar) used when a reminder names none |
| `system_apple_reminders_server_state_dir` | `~/.local/state/apple-reminders-server` | Role-managed runtime state: `meta.db`, signing cert, watchdog script, marker |
| `system_apple_reminders_server_db_path` | `<state_dir>/meta.db` | Sidecar SQLite database: id mapping, LWW timestamps, tombstones (see above) |
| `system_apple_reminders_server_backup_enabled` | `true` | Copy `meta.db` to `meta.db.bak-<ts>` before each deploy |
| `system_apple_reminders_server_backup_keep` | `7` | How many timestamped `meta.db` backups to retain |
| `system_apple_reminders_server_watchdog_enabled` | `true` | Deploy the liveness watchdog LaunchAgent |
| `system_apple_reminders_server_watchdog_interval` | `300` | Watchdog probe interval, seconds |
| `system_apple_reminders_server_watchdog_restart_cooldown` | `1800` | Minimum seconds between watchdog-triggered restarts |
| `system_apple_reminders_server_healthchecksio_enabled` | `true` | Create/attach a Healthchecks.io check for the watchdog to ping |
| `system_apple_reminders_server_healthchecksio_name` | `<host> - apple-reminders-server` | Healthchecks.io check name |
| `system_apple_reminders_server_keychain_password` | `""` | Login-keychain password, from vault. Needed only to provision the signing cert headlessly on the first run (see Permission stability) |

## Reaching it from Gateway

Gateway runs on `server-64gb-storage`, a different host, so this server is not
reachable over a shared Docker network. `composition-gateway` reaches it over
the infra zone that bertha serves, at
`apple-macmini-m4-16gb-malcolm.xberg.ber.{{ domainname_infra }}`. There is no
public DNS registration and no Traefik, since Malcolm runs no composition
roles at all.

## Checking status

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-reminders-server
launchctl print gui/$(id -u)/com.awfulwoman.apple-reminders-server-watchdog
tail -f ~/Code/awfulwoman/apple-reminders-server/logs/apple-reminders-server.log
tail -f ~/Code/awfulwoman/apple-reminders-server/logs/watchdog.log

# force a restart (e.g. after replacing meta.db)
launchctl kickstart -k gui/$(id -u)/com.awfulwoman.apple-reminders-server
```

A `running` state with `GET /reminders` returning 500 and
`attempt to write a readonly database` in the `.err` log means `meta.db` was
removed out from under the process — see the sidecar section above.
