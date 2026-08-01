# system-apple-contacts-server

Installs [`apple-contacts-server`](https://github.com/awfulwoman/apple-contacts-server)
as a per-user LaunchAgent on this host — a small authorised REST API in front of the
real macOS Contacts app (via the `Contacts` framework), used by
[`composition-gateway`](../composition-gateway) as its contacts backend (replacing
the previous Radicale/CardDAV backend).

## Requirements

- macOS only, and specifically **Malcolm** — the one host in this infra that's
  always logged into a GUI session, which the Contacts framework's TCC permission
  requires (a headless LaunchDaemon can never see the permission prompt or hold the
  grant).
- `uv` installed via Homebrew (this role installs it if absent).

The role clones/updates the `awfulwoman/apple-contacts-server` repo itself (via
SSH, into `system_apple_contacts_server_repo_dir`), so it no longer depends on
`system-repos` running first. Set `system_apple_contacts_server_repo_update: false`
to pin the checkout instead of pulling on every deploy.

## Permission stability (code signing)

macOS TCC pins the Contacts grant to a **code identity**. The role does **not**
launch via `uv run` (which spawns an ad-hoc-signed interpreter whose cdhash
changes on every `uv sync`/Python bump, silently dropping the grant). Instead it:

1. `uv sync`s the venv,
2. provisions a long-lived self-signed code-signing cert once
   (`scripts/setup_signing_cert.sh`, idempotent),
3. re-signs the interpreter with a fixed identifier on every deploy
   (`scripts/sign_runtime.sh`), and
4. launches the signed interpreter directly from the plist
   (`.venv/bin/python3 -m apple_contacts_server.main`).

TCC then matches on the cert + identifier, so the grant survives rebuilds. To
provision the cert **headlessly**, set
`system_apple_contacts_server_keychain_password` (from vault) so the role can run
`security set-key-partition-list` non-interactively — needed only on the first
provisioning run. If left empty, run `scripts/setup_signing_cert.sh` on Malcolm by
hand once (it prompts for keychain access — click "Always Allow"); later deploys
sign fine without it.

## One manual step this role cannot automate

The **first** time the LaunchAgent starts, macOS shows a Contacts permission
dialog in Malcolm's GUI session. Someone has to click "Allow" in person, once:

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-contacts-server | grep state
# if not "running", the permission dialog is likely waiting on-screen
```

Until that happens, the service starts but every Contacts framework call
blocks/fails. Thanks to the stable signature this is a **one-time** approval — it
no longer recurs after `uv sync` or Python upgrades.

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_apple_contacts_server_repo_dir` | `system_repos_base_dir/awfulwoman/apple-contacts-server` | Repo checkout to run from |
| `system_apple_contacts_server_port` | `4102` | Local port the service listens on |
| `system_apple_contacts_server_bearer_tokens` | `vault_gateway_contacts_server_token` | Shared secret — also set as `composition_gateway_contacts_server_bearer_token` |
| `system_apple_contacts_server_db_path` | `~/.local/state/apple-contacts-server/meta.db` | Sidecar SQLite — id mapping only, no LWW/tombstones (see the service's own README) |
| `system_apple_contacts_server_keychain_password` | `""` | Login-keychain password, from vault. Needed only to provision the signing cert headlessly on the first run (see Permission stability) |

## Reaching it from Gateway

Gateway runs on `server-64gb-storage`, a different host, so this isn't reachable over
a shared Docker network. `composition-gateway` reaches it over
Tailscale MagicDNS at `apple-macmini-m4-16gb-malcolm.{{ vault_tailscale_tailnet_name }}`
— no public DNS registration, no Traefik (Malcolm runs no composition roles at all).

## Checking status

```bash
ssh malcolm
launchctl print gui/$(id -u)/com.awfulwoman.apple-contacts-server
tail -f ~/Code/awfulwoman/apple-contacts-server/logs/apple-contacts-server.log
```
