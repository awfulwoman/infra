# system-promtail

Installs and configures [Grafana Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/) as a systemd service to ship logs to Loki. Downloads the correct architecture binary from GitHub releases (amd64/arm64/arm), configures log scraping for Docker container logs and systemd journal, and registers a systemd service.

Only reinstalls the binary when the installed version differs from `promtail_version`.
