# composition-loki

Deploys [Grafana Loki](https://grafana.com/oss/loki/) as a Docker Compose service for log aggregation. Configures a Loki config file with tunable ingestion rate limits and retention, sets correct ownership on the storage directory (uid/gid `10001`), and registers a Traefik subdomain via `network-register-subdomain`.

Storage is expected at `composition_loki_storage_path` (default `/slowpool/shared/logs/loki`), which must be provisioned separately.
