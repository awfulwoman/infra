# System MOTD

This role customizes the login message of the day (MOTD) on Ubuntu servers.
It disables Canonical's advertising and help-text MOTD scripts, and installs
a custom script that prints ZFS pool status at login.

## Design Notes

Ubuntu ships several MOTD scripts under `/etc/update-motd.d/` that display
news, help text, and ESM contract status. These are useful on workstations,
but noisy on servers. This role strips the execute bit from those scripts,
and preserves their timestamps, rather than deleting them. This keeps the
role idempotent, and makes it easy to re-enable a script by hand later.

The `99-zfspool` script is useful only on hosts with ZFS pools. It checks for
the `zpool` binary before it runs, so the role can deploy it safely even on
non-ZFS hosts, where it does nothing.

## Affected MOTD Scripts

- `/etc/update-motd.d/10-help-text`
- `/etc/update-motd.d/50-motd-news`
- `/etc/update-motd.d/91-contract-ua-esm-status`
