# system-promtail

Installs and configures [Grafana Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/) as a systemd service that ships logs to Loki. The role downloads the correct binary for the host architecture (amd64, arm64, or arm) from GitHub releases. It configures log scraping for Docker container logs and the systemd journal, and registers a systemd service.

Only reinstalls the binary when the installed version differs from `promtail_version`.
