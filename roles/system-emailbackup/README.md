# system-emailbackup

Backs up email from an IMAP mailbox to local ZFS storage using [isync](https://isync.sourceforge.io/) (`mbsync`). Installs `isync` via apt, writes an `mbsyncrc` config from a Jinja2 template, and creates a systemd service/timer pair to sync on the configured schedule.

Requires the storage path (`emailbackup_storage_path`, default `/slowpool/charlie/email`) to be pre-provisioned by `system-zfs`; the role fails fast if it does not exist.
