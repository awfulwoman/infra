# ZFS API

REST API for monitoring ZFS pools, datasets, snapshots, and backups.

## Overview

This composition provides a FastAPI-based REST API that exposes read-only ZFS status information. It integrates with the existing `system-zfs-policy` infrastructure to provide policy-aware snapshot monitoring via the `zfs-snapshot-report` tool.

**Key Features:**
- Pool health and capacity monitoring
- Dataset space usage and properties
- Policy-aware snapshot compliance tracking
- Backup status overview
- **Prometheus metrics endpoint** for VictoriaMetrics/Prometheus integration
- Interactive API documentation (Swagger UI)
- Automatic SSL via Traefik reverse proxy

## Architecture

**Stack:**
- **FastAPI**: Modern Python web framework with automatic OpenAPI docs
- **Uvicorn**: High-performance ASGI server
- **Docker**: Containerized deployment
- **Traefik**: Reverse proxy with automatic HTTPS

**Access:**
```
Client → Tailscale → Traefik → FastAPI Container → ZFS Commands
```

The container runs in privileged mode with access to `/dev/zfs` for read-only ZFS operations.

## API Endpoints

### Pools

- `GET /api/v1/pools` - List all pools with metrics
- `GET /api/v1/pools/{pool}` - Get specific pool info
- `GET /api/v1/pools/{pool}/status` - Detailed pool status (zpool status)
- `GET /api/v1/pools/{pool}/iostat` - Pool I/O statistics
- `GET /api/v1/pools/_version` - ZFS version information

### Datasets

- `GET /api/v1/datasets` - List all datasets
- `GET /api/v1/datasets/{dataset}` - Get dataset properties
- `GET /api/v1/datasets/{dataset}/snapshots` - List dataset snapshots

### Snapshots

- `GET /api/v1/snapshots` - Comprehensive snapshot report (uses zfs-snapshot-report)
- `GET /api/v1/snapshots/{dataset}` - Detailed snapshots for a dataset
- `GET /api/v1/snapshots/_all` - All snapshots across all datasets

### Backups

- `GET /api/v1/backups` - Backup status overview
- `GET /api/v1/backups/logs` - List available backup logs
- `GET /api/v1/backups/logs/{filename}` - Get backup log content

### System

- `GET /api/v1/health` - API health check
- `GET /api/docs` - Interactive API documentation (Swagger UI)
- `GET /api/redoc` - Alternative API documentation (ReDoc)

### Monitoring

- `GET /metrics` - Prometheus metrics endpoint (for VictoriaMetrics/Prometheus scraping)

## Configuration

### Role Variables

```yaml
# Enable/disable the composition
composition_zfs_api_enabled: true

# Application settings
composition_zfs_api_port: 8000
composition_zfs_api_log_level: "info"  # debug, info, warning, error

# Domain configuration
composition_zfs_api_subdomain: "zfs-api"
composition_zfs_api_domain: "{{ composition_zfs_api_subdomain }}.{{ host_pfqdn }}"

# Traefik integration
composition_zfs_api_traefik_enabled: true

# Command timeout (seconds)
composition_zfs_api_command_timeout: 30
```

### Host Requirements

This role requires:
- `zfs` variable defined in host_vars (ZFS must be configured)
- `system-zfs-policy` role deployed (for snapshot reporting)
- Traefik reverse proxy running (if using `composition_zfs_api_traefik_enabled`)

### Example Host Configuration

```yaml
# In host_vars/storage/core.yaml
roles:
  - system-zfs
  - system-zfs-policy
  - composition-reverseproxy
  - composition-zfs-api
```

## Usage Examples

### Query Pool Health

```bash
curl -s https://zfs-api.storage.xberg.ber.yourdomain.com/api/v1/pools | jq
```

```json
{
  "pools": [
    {
      "name": "fastpool",
      "health": "ONLINE",
      "size_bytes": 1920383410176,
      "capacity_percent": 42,
      "size_human": "1.75 TB"
    }
  ]
}
```

### Check Snapshot Compliance

```bash
curl -s https://zfs-api.storage.xberg.ber.yourdomain.com/api/v1/snapshots | jq
```

```json
{
  "hostname": "storage",
  "datasets": [
    {
      "dataset": "fastpool/compositions",
      "policy": "critical",
      "counts": {"hourly": 32, "daily": 28, "monthly": 3, "yearly": 5},
      "retention": {"hourly": 36, "daily": 30, "monthly": 3, "yearly": 5},
      "compliance": {"hourly": 89, "daily": 93, "monthly": 100, "yearly": 100}
    }
  ],
  "summary": {
    "total_datasets": 15,
    "total_snapshots": 482,
    "avg_compliance": 94
  }
}
```

### Find Low Compliance Datasets

```bash
curl -s https://zfs-api.storage.xberg.ber.yourdomain.com/api/v1/snapshots | \
  jq '.datasets[] | select(.compliance.daily < 90)'
```

### Get Dataset Details

```bash
curl -s https://zfs-api.storage.xberg.ber.yourdomain.com/api/v1/datasets/fastpool/compositions | jq
```

### Query Prometheus Metrics

```bash
# View all Prometheus metrics
curl https://zfs-api.storage.xberg.ber.yourdomain.com/metrics

# Filter specific metrics
curl -s https://zfs-api.storage.xberg.ber.yourdomain.com/metrics | grep zfs_pool_capacity

# Check metric format
curl -s https://zfs-api.storage.xberg.ber.yourdomain.com/metrics | head -20
```

### Monitor with Shell Script

```bash
#!/bin/bash
# Check ZFS health and alert on issues

API_URL="https://zfs-api.storage.xberg.ber.yourdomain.com/api/v1"

# Check pool health
UNHEALTHY=$(curl -s "$API_URL/pools" | jq -r '.pools[] | select(.health != "ONLINE") | .name')

if [ -n "$UNHEALTHY" ]; then
  echo "ALERT: Unhealthy pools: $UNHEALTHY"
fi

# Check snapshot compliance
LOW_COMPLIANCE=$(curl -s "$API_URL/snapshots" | jq -r '.alerts.low_compliance_datasets[] | .dataset')

if [ -n "$LOW_COMPLIANCE" ]; then
  echo "WARNING: Low snapshot compliance on: $LOW_COMPLIANCE"
fi
```

## Integration

### Home Assistant

Use the REST sensor platform:

```yaml
sensor:
  - platform: rest
    name: "ZFS Storage Health"
    resource: https://zfs-api.storage.xberg.ber.yourdomain.com/api/v1/pools/fastpool
    value_template: "{{ value_json.health }}"
    json_attributes:
      - capacity_percent
      - size_human
      - free_human

  - platform: rest
    name: "ZFS Snapshot Compliance"
    resource: https://zfs-api.storage.xberg.ber.yourdomain.com/api/v1/snapshots
    value_template: "{{ value_json.summary.avg_compliance }}"
    unit_of_measurement: "%"
```

### Prometheus / VictoriaMetrics

The API natively exposes Prometheus metrics at `/metrics`:

**Scrape Configuration:**
```yaml
scrape_configs:
  - job_name: 'zfs-metrics'
    scrape_interval: 60s
    static_configs:
      - targets:
          - 'zfs-api.host-storage.xberg.ber.domain.com:8000'
          - 'zfs-api.host-homeassistant.xberg.ber.domain.com:8000'
          - 'zfs-api.dns.xberg.ber.domain.com:8000'
          - 'zfs-api.host-backups.xberg.ber.domain.com:8000'
          - 'zfs-api.host-albion.location.city.domain.com:8000'
        labels:
          job: 'zfs'
          environment: 'homelab'
```

**Available Metrics:**
- `zfs_pool_health` - Pool health status (1=ONLINE, 0=other)
- `zfs_pool_capacity_percent` - Pool capacity percentage
- `zfs_pool_size_bytes` - Pool total size in bytes
- `zfs_pool_allocated_bytes` - Pool allocated bytes
- `zfs_pool_free_bytes` - Pool free bytes
- `zfs_pool_fragmentation_percent` - Pool fragmentation percentage
- `zfs_dataset_used_bytes` - Dataset used space
- `zfs_dataset_available_bytes` - Dataset available space
- `zfs_dataset_referenced_bytes` - Dataset referenced space
- `zfs_snapshot_count` - Number of snapshots
- `zfs_snapshot_retention` - Retention target
- `zfs_snapshot_compliance_percent` - Compliance percentage

**PromQL Query Examples:**
```promql
# Pool capacity across all hosts
zfs_pool_capacity_percent

# Pools over 80% capacity
zfs_pool_capacity_percent > 80

# Average snapshot compliance by policy
avg by (policy, interval) (zfs_snapshot_compliance_percent)

# Datasets with low compliance
zfs_snapshot_compliance_percent{interval="daily"} < 90

# Storage growth rate (bytes per day)
rate(zfs_pool_allocated_bytes[7d]) * 86400
```

## Security

**Read-Only Operations:**
All endpoints perform read-only operations. The API cannot modify ZFS pools, datasets, or snapshots.

**Network Access:**
The API is exposed via Traefik reverse proxy and is only accessible within your Tailscale network.

**Container Privileges:**
The container requires privileged mode to access `/dev/zfs`. This is necessary for ZFS commands but limited to read operations.

**Future Enhancements:**
- API key authentication
- Rate limiting
- Request logging and audit trails

## Development

### Local Testing

```bash
cd /var/compositions/zfs-api

# Build and start
docker-compose up --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### API Documentation

Once running, visit:
- Swagger UI: `https://zfs-api.storage.../api/docs`
- ReDoc: `https://zfs-api.storage.../api/redoc`
- OpenAPI spec: `https://zfs-api.storage.../api/openapi.json`

## Troubleshooting

### Container won't start

Check ZFS device access:
```bash
docker exec zfs-api zpool list
```

### API returns 500 errors

Check logs:
```bash
docker logs zfs-api
```

### Snapshot report fails

Verify zfs-snapshot-report is installed:
```bash
docker exec zfs-api /opt/zfs-policy/zfs-snapshot-report --json
```

### Traefik routing issues

Check Traefik dashboard and container labels:
```bash
docker inspect zfs-api | jq '.[0].Config.Labels'
```

## Related Roles

- `system-zfs` - ZFS pool and dataset management
- `system-zfs-policy` - Snapshot policies and automation
- `composition-reverseproxy` - Traefik reverse proxy
- `backups-zfs-server` - ZFS backup server (pull/push scripts)
