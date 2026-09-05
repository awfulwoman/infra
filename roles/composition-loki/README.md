# composition-loki

This role deploys [Grafana Loki](https://grafana.com/oss/loki/) as a Docker Compose service for log aggregation. It configures a Loki config file with tunable ingestion rate limits and retention, sets correct ownership on the storage directory (uid/gid `10001`), and registers a Traefik subdomain through `network-register-subdomain`.

You must provision storage separately, at `composition_loki_storage_path` (default `/slowpool/shared/logs/loki`).
