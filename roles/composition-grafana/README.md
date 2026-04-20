# Grafana

[Grafana OSS](https://grafana.com/oss/grafana/) visualization platform. Provisioned with VictoriaMetrics (Prometheus-compatible) and Loki datasources, pre-built dashboards for ZFS and infrastructure monitoring, and alerting via email.

## Ports

| Port | Service |
|------|---------|
| `3100` (`composition_grafana_port`) | Grafana web UI |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | Grafana database and persistent state |
| `{{ composition_config }}/provisioning` | Datasources, dashboards, and alerting config |

## Key Variables

| Variable | Purpose |
|----------|---------|
| `composition_grafana_admin_user` | Admin username (`vault_grafana_admin_user`, default: `admin`) |
| `composition_grafana_admin_password` | Admin password (`vault_grafana_admin_password`) |
| `composition_grafana_victoriametrics_url` | VictoriaMetrics URL (default: `https://zfs.metrics.{{ domain_name }}`) |
| `composition_grafana_loki_url` | Loki URL (default: `https://loki.{{ domain_name }}`) |
| `composition_grafana_traefik_enabled` | Toggle Traefik labels (default: `true`) |
| `composition_grafana_default_theme` | UI theme (default: `dark`) |

## Provisioned Datasources

- **VictoriaMetrics** — default Prometheus-compatible datasource, 60s scrape interval alignment.
- **Loki** — log aggregation datasource, max 1000 lines.

## Provisioned Dashboards

Static dashboards in `files/dashboards/`:

- `zfs-overview.json` — cluster-wide ZFS pool health, capacity, dataset usage, and snapshot compliance.
- `loki-docker-health.json` — Docker container health from Loki logs.
- `loki-infrastructure-overview.json` — infrastructure-wide log overview.
- `loki-security-audit.json` — security-relevant log events.
- `nginx-web-traffic.json` — nginx access log metrics.

Per-host ZFS dashboards are generated dynamically at deploy time by `templates/generate_host_dashboards.py.j2` using the Ansible `zfs` inventory group.

## Alerting

- Contact point: email to `alert@{{ vault_personal_domain }}` via SMTP (`vault_smtp_*`).
- Alert rule: **ZFS Pool Not ONLINE** — fires when `zfs_pool_health < 1` for 2+ minutes.
- Notification policy: group by folder + alertname, repeat every 4h.

## Integrations

- **Traefik**: Exposed at `grafana.{{ domain_name }}` with Let's Encrypt TLS.
- **composition-victoriametrics**: Primary metrics datasource.
- **Loki** (separate composition): Log datasource.
- **network-register-subdomain**: Registers the `grafana` subdomain.
