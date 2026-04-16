# DMARC Report Viewer

Lightweight standalone viewer for DMARC and SMTP TLS reports. Polls an IMAP
mailbox, parses incoming aggregate reports, and renders them in a web UI.

Reports are held in memory only; restarting the container re-reads everything
from IMAP, so the mailbox is the source of truth.

* [Homepage](https://github.com/cry-inc/dmarc-report-viewer)

## Required vault variables

Add to the host's `vault_core.yaml` (or similar):

```yaml
vault_dmarc_imap_host: imap.example.com
vault_dmarc_imap_user: dmarc@example.com
vault_dmarc_imap_password: hunter2
vault_dmarc_http_user: admin
vault_dmarc_http_password: hunter2
```

Optionally override `dmarc_imap_dmarc_folder` / `dmarc_imap_tls_folder` in
host vars if reports land somewhere other than `INBOX`.
