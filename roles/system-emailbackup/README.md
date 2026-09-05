# system-emailbackup

Backs up one or more IMAP mailboxes to local ZFS storage using
[isync](https://isync.sourceforge.io/) (`mbsync`). Each account configured in
`emailbackup_accounts` gets its own mbsync channel, its own
`emailbackup@<name>.service`/`.timer` pair, its own Maildir subdirectory under
`emailbackup_storage_path`, and — when `emailbackup_healthchecksio_enabled` is
set — its own [Healthchecks.io](https://healthchecks.io) dead-man's-switch check.

Requires the storage path (`emailbackup_storage_path`, default
`/slowpool/charlie/email`) to be pre-provisioned by `system-zfs`; the role fails
fast if it does not exist.

## Why per-account, and why the alerting

This role originally backed up a single mailbox with one non-templated
`emailbackup.service`/`.timer` and no failure notification of any kind. An audit
in September 2026 found the unit had failed **every recorded run for at least a
month** — a stale local folder (a mail folder deleted server-side, which mbsync's
default `Remove None` never reconciles) made mbsync exit 1 on every run, and
nothing surfaced that anywhere. Mail was still syncing correctly underneath the
failing exit code, which is exactly why it went unnoticed.

Two changes address this:

1. **Per-account units.** One account's mbsync failure (a bad password, a
   vanished folder, a transient IMAP error) no longer silently blocks or hides
   behind another account's success — each account is its own unit with its own
   result.
2. **A Healthchecks.io check per account**, pinged from a wrapper script that
   sends an **explicit success or `/fail` signal** based on mbsync's exit code —
   not just a bare success ping relying on the grace-period timeout to notice
   silence. A failing account is reported immediately.

See `docs/superpowers/specs/2026-09-04-mail-archive-server-handoff.md` §4 in the
`gateway` repo for the full incident writeup this role update is based on.

## Migrating an already-populated host to multi-account

If this role has run before on this host under the old single-account layout
(mail folders directly under `emailbackup_storage_path`, e.g. `.../INBOX`), you
**must** migrate the existing data before applying the updated role — otherwise
the role will treat the host as having no data yet and mbsync will re-download
everything from scratch under the new `emailbackup_storage_path/<account>/` path.

Run `files/migrate-to-multi-account.sh` **on the storage host itself**, as the
user that owns the Maildir, before the next Ansible run:

```
scp roles/system-emailbackup/files/migrate-to-multi-account.sh <host>:/tmp/
ssh <host>
/tmp/migrate-to-multi-account.sh --dry-run personal /slowpool/charlie/email
/tmp/migrate-to-multi-account.sh             personal /slowpool/charlie/email
```

It stops the old units, records a before/after file-count and `du -sh` baseline,
verifies the three folders known to be stale on the original single-account host
(`Amazon`, `INBOX/Amazon`, `Later`) are genuinely empty before removing them —
refusing outright if any of them unexpectedly contain messages — then moves every
remaining folder and its mbsync state file into `<account>/`. Because mbsync's
state files are named by mailbox with no channel prefix, relocating them
alongside the Maildir preserves sync state exactly: applying the role afterwards
and running `emailbackup@<account>.service` for the first time should pull
**zero** new messages. A large re-download means the state files ended up in the
wrong place — stop and investigate rather than letting it re-fetch everything.

It is idempotent — it refuses to run again once `emailbackup_storage_path/<account>/`
already exists — and every step is `--dry-run`-able.

## An open question this role deliberately leaves open: `Remove Near`

`mbsyncrc.j2` does **not** set `Remove`, so it defaults to `None`: mbsync never
reconciles a folder that vanished on the far side, which is exactly what caused
the silent-failure incident above (a permanently erroring pair, forever). Setting
`Remove Near` would fix that — but per `man mbsync`, "for safety, non-empty
mailboxes are never deleted," and it is **not documented** whether a
non-empty-but-vanished box still errors under `Remove Near`. That distinction
matters: if it does still error, that's arguably correct (a folder disappearing
server-side *with* mail in it is something worth being told about); if it
silently deletes local mail once the far side is gone, that changes what
`Expunge None` is protecting.

Before adopting `Remove Near`, test deliberately (create a remote folder, sync,
put mail in the local copy, delete the remote folder, sync again) and record the
answer here. Until then, treat "far side box cannot be opened" as an expected,
alertable condition — the healthchecks `/fail` ping now makes that reporting
loud — rather than routing around it by ignoring mbsync's exit code.

## Variables

| Variable | Default | Description |
|---|---|---|
| `emailbackup_accounts` | one account, from `vault_mailprovider_*` | List of `{name, imap_host, imap_user, imap_password, patterns?}`. `name` becomes a directory, a systemd instance name, and (via mail-archive-server) an API account name — keep it matching `^[a-z0-9][a-z0-9_-]*$` |
| `emailbackup_sync_schedule` | `hourly` | `hourly`/`daily`/`weekly`, applied to every account's timer |
| `emailbackup_storage_path` | `/slowpool/charlie/email` | Maildir root; one subdirectory per account |
| `emailbackup_healthchecksio_enabled` | `false` | Per-account dead-man's-switch checks |
| `emailbackup_healthchecksio_api_key` | `vault_healthchecks_rw_apikey` | |
| `emailbackup_healthchecksio_tz` | `Europe/Berlin` | |
| `emailbackup_script_dir` | `/usr/local/lib/emailbackup` | Where per-account wrapper scripts are installed |

## Upgrading from the old non-templated units

The role detects and removes the old `emailbackup.service`/`.timer` unit files
itself (stop, disable, delete, reload) — no manual cleanup needed there. Only the
**data migration** above needs a manual, out-of-band step.
