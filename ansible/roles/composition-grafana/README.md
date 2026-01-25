# composition-grafana

Grafana visualization platform for ZFS metrics collected by VictoriaMetrics.

## Overview

Deploys Grafana OSS edition with:

- Pre-configured VictoriaMetrics datasource
- Provisioned ZFS Overview dashboard
- HTTPS access via Traefik
- Automatic dashboard updates

## Architecture

**Host:** host-storage (same as VictoriaMetrics)

**Components:**

- Grafana OSS container
- VictoriaMetrics datasource at `zfs.metrics.{{ domain_name }}`
- ZFS Overview dashboard with 7 panels
- Traefik reverse proxy integration

**Access:** `https://grafana.{{ domain_name }}`

## Configuration

### Required Vault Variables

Add to `ansible/inventory/group_vars/infra/vault_compositions.yaml`:

```yaml
vault_grafana_admin_user: "admin"
vault_grafana_admin_password: "<secure-password>"
```

### Default Settings

See `defaults/main.yaml` for all configurable options:
- Port: 3000
- Default theme: dark
- Datasource: VictoriaMetrics at `https://zfs.metrics.{{ domain_name }}`
- Telemetry: disabled

## Dashboards

### ZFS Overview

Cluster-wide ZFS overview dashboard with 6 panels:

1. **Pool Capacity** - Gauge showing capacity % per pool
   - Green: <70%, Yellow: 70-85%, Red: >85%

2. **Pool Health Status** - Status indicators per pool
   - Green: ONLINE, Red: DEGRADED/FAULTED

3. **Dataset Space by Host** - Stacked area chart
   - Total dataset usage per host over time

4. **Top 10 Datasets by Space Usage** - Pie chart
   - Largest datasets across all hosts

5. **Snapshot Compliance by Policy** - Table view
   - Compliance % by host, policy, interval
   - Green: >95%, Yellow: 80-95%, Red: <80%

6. **Snapshot Count Trends** - Time series
   - Snapshot counts by host and policy over time

**Auto-refresh:** 1 minute
**Default time range:** Last 24 hours
**Location:** ZFS folder in Grafana

### Per-Host Detailed Dashboards

Individual dashboards for each ZFS host with detailed breakdown.

**Hosts:** Dynamically generated from Ansible `zfs` inventory group

**Sections:**

1. **Pool Status** - Capacity gauges, health status per pool
2. **Datasets** - Sortable table of all datasets with usage, top 10 trending
3. **Snapshots** - Compliance table per dataset/policy/interval, count trends

**Auto-refresh:** 1 minute
**Location:** ZFS folder in Grafana
**UIDs:** `zfs-{hostname}` (e.g., `zfs-hoststorage`)

## Deployment

### Deploy Grafana

```bash
# Deploy to host-storage
ansible-playbook ansible/playbooks/baremetal/host-storage/victoriametrics.yaml
```

### Verify Deployment

```bash
# Check container status
ssh host-storage 'docker ps | grep grafana'

# Check logs
ssh host-storage 'docker logs grafana'

# Test web interface
curl -I https://grafana.{{ domain_name }}
```

### First Login

1. Navigate to `https://grafana.{{ domain_name }}`
2. Login with vault credentials
3. Dashboard available at: Dashboards → ZFS → ZFS Overview
4. VictoriaMetrics datasource pre-configured

## Provisioning

### Datasources

Datasource provisioning via `/etc/grafana/provisioning/datasources/`:
- VictoriaMetrics configured as default Prometheus-compatible datasource
- HTTPS connection to `https://zfs.metrics.{{ domain_name }}`
- 60s scrape interval alignment

### Dashboard Provisioning

Dashboard provisioning via `/etc/grafana/provisioning/dashboards/`:

- ZFS Overview: Static dashboard from `files/dashboards/zfs-overview.json`
- Per-Host Dashboards: Generated dynamically from
  `templates/generate_host_dashboards.py.j2` using Ansible `zfs` inventory
  group
- Updates applied on Grafana restart
- User modifications allowed (`allowUiUpdates: true`)

## Adding Custom Dashboards

1. Create dashboard JSON in `files/dashboards/`
2. Grafana will auto-load on next provisioning refresh (10s interval)
3. Or restart container: `docker restart grafana`

## Dynamic Dashboard Generation

Per-host ZFS dashboards are generated dynamically during deployment:

1. `generate_host_dashboards.py.j2` template reads hosts from Ansible `zfs` group
2. Ansible templates the script to target host
3. Script executes to generate dashboard JSON for each host
4. Generated dashboards are provisioned to Grafana
5. Script is removed after generation

To regenerate dashboards (e.g., after adding hosts to `zfs` group):

```bash
ansible-playbook ansible/playbooks/baremetal/host-storage/victoriametrics.yaml
```

## Metrics Available

From VictoriaMetrics datasource:

**Pool Metrics:**
- `zfs_pool_health` - Health status (1=ONLINE, 0=other)
- `zfs_pool_capacity_percent` - Capacity percentage
- `zfs_pool_size_bytes` - Total pool size
- `zfs_pool_allocated_bytes` - Allocated space
- `zfs_pool_free_bytes` - Free space

**Dataset Metrics:**
- `zfs_dataset_used_bytes` - Used space
- `zfs_dataset_available_bytes` - Available space
- `zfs_dataset_referenced_bytes` - Referenced space

**Snapshot Metrics:**
- `zfs_snapshot_count` - Number of snapshots
- `zfs_snapshot_retention` - Retention target
- `zfs_snapshot_compliance_percent` - Compliance %

All metrics labeled with: `hostname`, `pool`, `dataset`, `policy`,
`interval`

## Query Examples

### Pool Capacity Above 80%

```promql
zfs_pool_capacity_percent > 80
```

### Average Snapshot Compliance by Policy

```promql
avg by (policy) (zfs_snapshot_compliance_percent)
```

### Total Dataset Usage Per Host

```promql
sum by (hostname) (zfs_dataset_used_bytes)
```

### Pools Not ONLINE

```promql
zfs_pool_health{state!="ONLINE"}
```

## Troubleshooting

### Dashboard Not Loading

```bash
# Check provisioning logs
ssh host-storage 'docker logs grafana | grep provisioning'

# Verify dashboard file exists
ssh host-storage \
  'ls -la /opt/compositions/grafana/config/provisioning/dashboards/'
```

### Datasource Connection Failed

```bash
# Test VictoriaMetrics accessibility from Grafana container
ssh host-storage \
  'docker exec grafana curl -I https://zfs.metrics.{{ domain_name }}'

# Check datasource provisioning
ssh host-storage \
  'cat /opt/compositions/grafana/config/provisioning/datasources/victoriametrics.yaml'
```

### No Data in Panels

```bash
# Verify VictoriaMetrics has data
curl -s 'https://zfs.metrics.{{ domain_name }}/api/v1/query' \
  --data-urlencode 'query=zfs_pool_capacity_percent' | jq

# Check time range - ensure it matches data retention
# Default: 24h, VictoriaMetrics retention: 1y
```

### Permission Errors

```bash
# Check ownership of Grafana data directory
ssh host-storage 'ls -la /opt/compositions/grafana/config/data/'

# Should be owned by {{ ansible_user }}:{{ ansible_user_gid }}
# Container runs as user {{ ansible_user_uid }}
```

## File Structure

```text
ansible/roles/composition-grafana/
├── README.md
├── defaults/main.yaml                   # Configuration variables
├── meta/main.yaml                       # Role dependencies
├── tasks/main.yaml                      # Ansible tasks
├── templates/
│   ├── docker-compose.yaml.j2           # Container definition
│   ├── environment_vars.j2              # Grafana env vars
│   ├── generate_host_dashboards.py.j2   # Per-host dashboard generator
│   └── provisioning/
│       ├── datasources.yaml.j2          # VictoriaMetrics datasource
│       └── dashboards.yaml.j2           # Dashboard provider config
└── files/
    └── dashboards/
        └── zfs-overview.json            # ZFS Overview dashboard
```

## Dependencies

- `composition-common` - Base composition setup
- `composition-victoriametrics` - Datasource (must be running)
- `composition-reverseproxy` - Traefik for HTTPS
- `network-register-subdomain` - DNS registration

## Security

- Admin credentials stored in Ansible Vault
- Traefik handles TLS termination
- Telemetry and analytics disabled
- Gravatar disabled
- External snapshots disabled
- VictoriaMetrics connection via HTTPS with cert verification

## Related Roles

- `composition-victoriametrics` - Metrics storage and collection
- `composition-zfs-api` - ZFS metrics exposure
- `system-zfs-policy` - Snapshot policy management

## References

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [VictoriaMetrics as Prometheus](https://docs.victoriametrics.com/)
