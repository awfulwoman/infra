# system-apple-calendar-server

This role installs [`apple-calendar-server`](https://github.com/awfulwoman/apple-calendar-server)
as a per-user LaunchAgent on this host. It is a small authorized REST API in
front of the real macOS Calendar app, through `EventKit`.

It is the sibling of [`system-apple-reminders-server`](../system-apple-reminders-server).
It acts as the calendar backend for [`composition-gateway`](../composition-gateway).
It supports multiple calendars: `GET /calendars`, filtering by calendar, and
writes to named calendars.

## Requirements

- macOS only, and specifically **Malcolm**. Malcolm is the one host in this
  infra that stays logged into a GUI session at all times. EventKit's Calendar
  TCC permission needs this: a headless LaunchDaemon can never see the
  permission prompt or hold the grant.
- `uv`, installed through Homebrew. This role installs it if the host does not
  have it.

The role clones and updates the `awfulwoman/apple-calendar-server` repo itself,
over SSH, into `system_apple_calendar_server_repo_dir`. It does not depend on
`system-repos`. Set `system_apple_calendar_server_repo_update: false` to pin
the checkout instead of pulling on every deploy.

## Permission stability (code signing)

This works the same way as the reminders server. TCC pins the Calendar grant
to a **code identity**, so the role does **not** launch the server through
`uv run`. An ad-hoc-signed interpreter's cdhash changes on every `uv sync` or
Python upgrade, and this silently drops the grant.

Instead, the role runs `uv sync` and provisions a long-lived self-signed
code-signing cert once (`scripts/setup_signing_cert.sh`). It then re-signs the
interpreter with a fixed identifier on every deploy
(`scripts/sign_runtime.sh`). Finally, it launches the signed interpreter
directly (`.venv/bin/python3 -m apple_calendar_server.main`).

The calendar server uses its **own** signing cert
(`awfulwoman-apple-calendar-server-signing`) and identifier
(`com.awfulwoman.apple-calendar-server`), separate from the reminders server.
Calendar and Reminders need distinct TCC grants regardless.

To provision the cert **headlessly**, set
`system_apple_calendar_server_keychain_password` (from vault). This lets the
role run `security set-key-partition-list` without a prompt. You need this
only for the first provisioning run. If you leave it empty, run
`scripts/setup_signing_cert.sh` on Malcolm by hand once. Click "Always Allow"
when it prompts. Later deploys sign fine without it.

## One manual step this role cannot automate

The **first** time the LaunchAgent starts, macOS shows a Calendar permission
dialog in Malcolm's GUI session. Someone must click "Allow" in person, once:

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-calendar-server | grep state
# if not "running", the permission dialog is likely waiting on-screen
```

Thanks to the stable signature, this approval happens only once. It does not
recur after `uv sync` or Python upgrades.

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_apple_calendar_server_repo_dir` | `system_repos_base_dir/awfulwoman/apple-calendar-server` | Repo checkout to run from (cloned by this role) |
| `system_apple_calendar_server_port` | `4101` | Local port the service listens on |
| `system_apple_calendar_server_bearer_tokens` | `vault_gateway_calendar_server_token` | Shared secret. Add this vault key before you run the role |
| `system_apple_calendar_server_default_calendar` | `Calendar` | Calendar (EKCalendar) used when an event names none |
| `system_apple_calendar_server_window_past_days` / `_future_days` | `30` / `365` | Default `GET /events` window when the client sends no `start`/`end` |
| `system_apple_calendar_server_db_path` | `~/.local/state/apple-calendar-server/meta.db` | Sidecar SQLite database: id mapping, LWW timestamps, tombstones |
| `system_apple_calendar_server_keychain_password` | `""` | Login-keychain password, from vault. Needed only to provision the signing cert headlessly on the first run |

## Reaching it from Gateway

Gateway runs on `server-64gb-storage`, a different host. Gateway reaches this
server over the infra zone that bertha serves, at
`apple-macmini-m4-16gb-malcolm.xberg.ber.{{ domainname_infra }}` (port `4101`).
There is no public DNS and no Traefik. Wiring the Gateway side
(`composition-gateway`) is a separate change.

## Checking status

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-calendar-server
tail -f ~/Code/awfulwoman/apple-calendar-server/logs/apple-calendar-server.log
```
