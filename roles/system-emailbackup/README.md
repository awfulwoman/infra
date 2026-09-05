# system-emailbackup

This role backs up email from an IMAP mailbox to local ZFS storage, with
[isync](https://isync.sourceforge.io/) (`mbsync`). It installs `isync`
through apt and writes an `mbsyncrc` config from a Jinja2 template. It also
creates a systemd service and timer pair to sync mail on the configured
schedule.

`system-zfs` must pre-provision the storage path
(`emailbackup_storage_path`, default `/slowpool/charlie/email`). The role
fails fast if the path does not exist.
