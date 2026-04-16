# DMARC Report Viewer

Lightweight standalone viewer for DMARC and SMTP TLS reports. Polls an IMAP
mailbox, parses incoming aggregate reports, and renders them in a web UI.

Reports are held in memory only; restarting the container re-reads everything
from IMAP, so the mailbox is the source of truth.

* [Homepage](https://github.com/cry-inc/dmarc-report-viewer)

## Required vault variables

IMAP creds reuse the shared `vault_mailbox_*` vars from
`inventory/group_vars/infra/vault_mailbox.yaml` (same ones
`system-emailbackup` / nullmailer use). No new IMAP vault vars needed.

Web UI basic auth still needs its own vault vars on the host:

```yaml
vault_dmarc_http_user: admin
vault_dmarc_http_password: hunter2
```

Override `dmarc_imap_dmarc_folder` / `dmarc_imap_tls_folder` in host vars
if reports land somewhere other than `INBOX`.
