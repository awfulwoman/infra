# system-apple-calendar-server

Installs [`apple-calendar-server`](https://github.com/awfulwoman/apple-calendar-server)
as a per-user LaunchAgent on this host — a small authorised REST API in front of the
real macOS Calendar app (via `EventKit`), the sibling of
[`system-apple-reminders-server`](../system-apple-reminders-server), intended as
[`composition-gateway`](../composition-gateway)'s calendar backend. Supports multiple
calendars (`GET /calendars`, per-calendar filtering, writes to named calendars).

## Requirements

- macOS only, and specifically **Malcolm** — the one host in this infra that's
  always logged into a GUI session, which EventKit's Calendar TCC permission
  requires (a headless LaunchDaemon can never see the permission prompt or hold the
  grant).
- `uv` installed via Homebrew (this role installs it if absent).

The role clones/updates the `awfulwoman/apple-calendar-server` repo itself (via
SSH, into `system_apple_calendar_server_repo_dir`), so it does not depend on
`system-repos`. Set `system_apple_calendar_server_repo_update: false` to pin the
checkout instead of pulling on every deploy.

## Permission stability (code signing)

Identical to the reminders server: TCC pins the Calendar grant to a **code
identity**, so the role does **not** launch via `uv run` (an ad-hoc-signed
interpreter's cdhash changes on every `uv sync`/Python bump, silently dropping the
grant). Instead it `uv sync`s, provisions a long-lived self-signed code-signing
cert once (`scripts/setup_signing_cert.sh`), re-signs the interpreter with a fixed
identifier on every deploy (`scripts/sign_runtime.sh`), and launches the signed
interpreter directly (`.venv/bin/python3 -m apple_calendar_server.main`).

The calendar server uses its **own** signing cert
(`awfulwoman-apple-calendar-server-signing`) and identifier
(`com.awfulwoman.apple-calendar-server`), separate from the reminders server — they
need distinct TCC grants (Calendar vs Reminders) regardless.

To provision the cert **headlessly**, set
`system_apple_calendar_server_keychain_password` (from vault) so the role can run
`security set-key-partition-list` non-interactively — needed only on the first
provisioning run. If left empty, run `scripts/setup_signing_cert.sh` on Malcolm by
hand once (click "Always Allow"); later deploys sign fine without it.

## One manual step this role cannot automate

The **first** time the LaunchAgent starts, macOS shows a Calendar permission dialog
in Malcolm's GUI session. Someone has to click "Allow" in person, once:

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-calendar-server | grep state
# if not "running", the permission dialog is likely waiting on-screen
```

Thanks to the stable signature this is a **one-time** approval — it no longer
recurs after `uv sync` or Python upgrades.

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_apple_calendar_server_repo_dir` | `system_repos_base_dir/awfulwoman/apple-calendar-server` | Repo checkout to run from (cloned by this role) |
| `system_apple_calendar_server_port` | `4101` | Local port the service listens on |
| `system_apple_calendar_server_bearer_tokens` | `vault_gateway_calendar_server_token` | Shared secret — **add this vault key before running** |
| `system_apple_calendar_server_default_calendar` | `Calendar` | Calendar (EKCalendar) used when an event doesn't name one |
| `system_apple_calendar_server_window_past_days` / `_future_days` | `30` / `365` | Default `GET /events` window when the client sends no `start`/`end` |
| `system_apple_calendar_server_db_path` | `~/.local/state/apple-calendar-server/meta.db` | Sidecar SQLite — id mapping, LWW timestamps, tombstones |
| `system_apple_calendar_server_keychain_password` | `""` | Login-keychain password, from vault. Needed only to provision the signing cert headlessly on the first run |

## Reaching it from Gateway

Gateway runs on `server-64gb-storage`, a different host, so this is reached over
the infra zone that bertha serves, at `apple-macmini-m4-16gb-malcolm.xberg.ber.{{ domainname_infra }}`
(port `4101`) — no public DNS, no Traefik. Wiring the Gateway side
(`composition-gateway`) is a separate change.

## Checking status

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-calendar-server
tail -f ~/Code/awfulwoman/apple-calendar-server/logs/apple-calendar-server.log
```
