# System MOTD

Customises the login message of the day on Ubuntu servers. Disables Canonical's advertising and help-text MOTD scripts, and installs a custom script that prints ZFS pool status on login.

## Design Notes

Ubuntu ships several MOTD scripts under `/etc/update-motd.d/` that display news, help text, and ESM contract status — useful on workstations, noisy on servers. This role strips the execute bit from those scripts (preserving timestamps) rather than deleting them, which is cleaner for idempotency and makes it easy to re-enable manually if needed.

The `99-zfspool` script is only useful on hosts with ZFS pools. It checks for the `zpool` binary before running, so it's safe to deploy even on non-ZFS hosts where it will silently no-op.

## Affected MOTD Scripts

- `/etc/update-motd.d/10-help-text`
- `/etc/update-motd.d/50-motd-news`
- `/etc/update-motd.d/91-contract-ua-esm-status`
