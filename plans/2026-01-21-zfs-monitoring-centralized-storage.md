# Implementation Plan: ZFS Monitoring with Centralized Storage (GH #140)

**Date:** 2026-01-21
**Issue:** #140 - Monitoring of ZFS policy and backup status
**Status:** Planning

## Overview

Implement centralized monitoring and long-term storage for ZFS metrics across the infrastructure. Building upon the existing `composition-zfs-api` role, this will create a comprehensive monitoring solution that collects ZFS pool, dataset, snapshot, and backup status data from all ZFS hosts and stores it in a queryable time-series database.

## Current State

### What Exists
- ✅ `composition-zfs-api` role - FastAPI application with endpoints for:
  - Pool health and capacity (`/api/v1/pools`)
  - Dataset properties (`/api/v1/datasets`)
  - Snapshot compliance via `zfs-snapshot-report` (`/api/v1/snapshots`)
  - Backup status and logs (`/api/v1/backups`)
- ✅ **zfs-api deployed to 5 hosts:** host-storage, host-homeassistant, dns, host-backups, host-albion
- ✅ ZFS policy infrastructure via `system-zfs-policy` role
- ✅ All APIs accessible via HTTPS through Traefik

### What's Missing
- ❌ No Prometheus exporter to convert JSON → metrics format
- ❌ No centralized metrics collection system
- ❌ No long-term storage for historical data
- ❌ No query interface for stored metrics

### Not In Scope
- ⏭️ vm-awfulwoman-hetzner - Hetzner cloud host, monitoring deferred

## Architecture Decision

Based on requirements and homelab constraints:

**Time-series Database:** VictoriaMetrics
- Prometheus-compatible (PromQL support)
- Extremely efficient storage and resource usage
- Single binary deployment
- Built-in UI (vmui) for queries
- Future Grafana integration ready

**Collection Method:** Prometheus Exporter Pattern
- Lightweight Python exporter per host
- Converts zfs-api JSON → Prometheus metrics format
- Pull-based scraping by VictoriaMetrics
- Follows standard monitoring patterns

**Deployment Location:** host-storage
- Primary storage host with good resources
- Always available
- Logical home for storage monitoring

## Implementation Phases

### Phase 1: Verify ZFS API Deployment ✅

**Status:** COMPLETE - Already deployed to 5 hosts

**Deployed Hosts:**
- ✅ host-storage - `compositions: [zfs-api, ...]`
- ✅ host-homeassistant - `compositions: [zfs-api, ...]`
- ✅ dns - `compositions: [zfs-api, ...]`
- ✅ host-backups - `compositions: [zfs-api, ...]`
- ✅ host-albion - `compositions: [zfs-api, ...]`
- ⏭️ vm-awfulwoman-hetzner - Deferred

**Verification Tasks:**
```bash
# Test each host's API endpoints
for host in host-storage host-homeassistant dns host-backups host-albion; do
  echo "=== Testing $host ==="
  curl -s "https://zfs-api.${host}.xberg.ber.{domain}/api/v1/health" | jq .status
  curl -s "https://zfs-api.${host}.xberg.ber.{domain}/api/v1/pools" | jq '.pools[].name'
done
```

**Expected Output:**
Each host should return:
- Health status: `"healthy"`
- Pool names for that host
- Snapshot compliance data
- Backup status (where applicable)

### Phase 2: Create ZFS Prometheus Exporter

**Objective:** Convert zfs-api JSON responses to Prometheus metrics format

**New Role:** `composition-zfs-exporter`

**Files to Create:**
```
ansible/roles/composition-zfs-exporter/
├── README.md
├── defaults/main.yaml
├── tasks/main.yaml
├── templates/
│   ├── docker-compose.yaml.j2
│   └── environment_vars.j2
└── files/
    └── exporter/
        ├── Dockerfile
        ├── requirements.txt
        └── zfs_exporter.py
```

**Exporter Functionality:**
The Python exporter will:
1. Poll local zfs-api endpoints (http://localhost:8000)
2. Transform JSON responses into Prometheus metrics:
   ```
   # Pool metrics
   zfs_pool_health{pool="fastpool",state="ONLINE"} 1
   zfs_pool_capacity_percent{pool="fastpool"} 42
   zfs_pool_size_bytes{pool="fastpool"} 1920383410176
   zfs_pool_allocated_bytes{pool="fastpool"} 806561013760
   zfs_pool_free_bytes{pool="fastpool"} 1113822396416
   zfs_pool_fragmentation_percent{pool="fastpool"} 15

   # Dataset metrics
   zfs_dataset_used_bytes{pool="fastpool",dataset="compositions"} 523654123520
   zfs_dataset_available_bytes{pool="fastpool",dataset="compositions"} 890168272896
   zfs_dataset_referenced_bytes{pool="fastpool",dataset="compositions"} 503654123520

   # Snapshot compliance metrics
   zfs_snapshot_count{pool="fastpool",dataset="compositions",policy="critical",interval="hourly"} 32
   zfs_snapshot_retention{pool="fastpool",dataset="compositions",policy="critical",interval="hourly"} 36
   zfs_snapshot_compliance_percent{pool="fastpool",dataset="compositions",policy="critical",interval="hourly"} 89

   # Backup metrics
   zfs_backup_last_success_timestamp{source="host-storage",destination="host-backups"} 1737456000
   zfs_backup_duration_seconds{source="host-storage",destination="host-backups"} 1234
   ```

3. Expose metrics on `:9101/metrics`
4. Include metadata: hostname, pool names, dataset names, policy names

**Exporter Configuration:**
```yaml
# Role variables
composition_zfs_exporter_enabled: true
composition_zfs_exporter_port: 9101
composition_zfs_exporter_zfs_api_url: "http://zfs-api:8000"
composition_zfs_exporter_scrape_interval: 60  # seconds
```

**Deployment:**
- Deploy exporter to same 5 hosts as zfs-api
- Run as sidecar container in same Docker Compose stack
- No Traefik exposure needed (internal scraping only)
- Target hosts: host-storage, host-homeassistant, dns, host-backups, host-albion

### Phase 3: Deploy VictoriaMetrics

**Objective:** Central time-series database for long-term metric storage

**New Role:** `composition-victoriametrics`

**Files to Create:**
```
ansible/roles/composition-victoriametrics/
├── README.md
├── defaults/main.yaml
├── tasks/main.yaml
└── templates/
    ├── docker-compose.yaml.j2
    └── prometheus.yaml.j2  # Scrape configuration
```

**VictoriaMetrics Configuration:**
```yaml
# Deploy only to host-storage
composition_victoriametrics_enabled: true
composition_victoriametrics_port: 8428
composition_victoriametrics_ui_port: 8429  # vmui interface
composition_victoriametrics_subdomain: "metrics"
composition_victoriametrics_retention: "1y"  # 1 year retention

# Data storage
composition_victoriametrics_storage_path: "/var/lib/victoriametrics"
composition_victoriametrics_storage_size: "50Gi"  # Adjust based on needs
```

**Scrape Configuration (prometheus.yaml):**
```yaml
global:
  scrape_interval: 60s
  evaluation_interval: 60s

scrape_configs:
  - job_name: 'zfs-metrics'
    static_configs:
      # 5 ZFS hosts with monitoring enabled
      - targets:
          - 'zfs-exporter.host-storage.xberg.ber.{domain}:9101'
          - 'zfs-exporter.host-homeassistant.xberg.ber.{domain}:9101'
          - 'zfs-exporter.dns.xberg.ber.{domain}:9101'
          - 'zfs-exporter.host-backups.xberg.ber.{domain}:9101'
          - 'zfs-exporter.host-albion.{location}.{city}.{domain}:9101'
        labels:
          job: 'zfs'
          environment: 'homelab'
```

**VictoriaMetrics Features:**
- Single-node deployment (sufficient for homelab)
- Prometheus remote write compatible
- PromQL query support
- Built-in vmui web interface
- Automatic deduplication
- Efficient compression

**Endpoints:**
- Metrics ingestion: `https://metrics.host-storage.../api/v1/write`
- Query API: `https://metrics.host-storage.../api/v1/query`
- Web UI: `https://metrics.host-storage.../vmui`

### Phase 4: Testing and Validation

**Objective:** Verify end-to-end data flow and querying

**Test Cases:**

1. **Exporter Health:**
   ```bash
   # Verify exporters are running on all 5 hosts
   for host in host-storage host-homeassistant dns host-backups host-albion; do
     curl -s http://zfs-exporter.${host}...:9101/metrics | head -5
   done
   ```

2. **VictoriaMetrics Ingestion:**
   ```bash
   # Check if metrics are being scraped
   curl -s 'https://metrics.host-storage.../api/v1/query?query=up{job="zfs"}' | jq
   ```

3. **Query Historical Data:**
   ```promql
   # Pool capacity over time
   zfs_pool_capacity_percent{pool="fastpool"}[24h]

   # Snapshot compliance trends
   avg by (dataset) (zfs_snapshot_compliance_percent)

   # Backup success rate
   rate(zfs_backup_last_success_timestamp[7d])
   ```

4. **Validate Compliance Tracking:**
   ```promql
   # Find datasets with low compliance
   zfs_snapshot_compliance_percent < 90

   # Alert on missing snapshots
   (time() - zfs_snapshot_last_created_timestamp) > 7200  # 2 hours
   ```

### Phase 5: Documentation and Query Patterns

**Objective:** Document how to query and use the stored metrics

**Documentation to Create:**
- Query examples in VictoriaMetrics README
- Common PromQL patterns for ZFS monitoring
- Alerting rule examples (for future Alertmanager integration)
- Dashboard JSON examples (for future Grafana)

**Example Queries:**

```promql
# Top 5 datasets by space usage
topk(5, zfs_dataset_used_bytes)

# Pool health status (1 = ONLINE)
zfs_pool_health{state="ONLINE"}

# Datasets exceeding 80% capacity
(zfs_dataset_used_bytes / (zfs_dataset_used_bytes + zfs_dataset_available_bytes)) > 0.8

# Snapshot policy compliance summary
avg by (policy, interval) (zfs_snapshot_compliance_percent)

# Backup age in hours
(time() - zfs_backup_last_success_timestamp) / 3600

# Storage growth rate (GB/day)
rate(zfs_pool_allocated_bytes[7d]) * 86400 / 1073741824
```

## Migration Path and Rollout

**Step-by-step Deployment:**

1. **~~Week 1:~~ Deploy zfs-api to all hosts** ✅ COMPLETE
   - zfs-api already deployed to 5 hosts
   - All endpoints verified working
   - vm-awfulwoman-hetzner deferred

2. **Week 1:** Develop and test exporter
   - Create `composition-zfs-exporter` role
   - Test locally on host-storage
   - Deploy to all ZFS hosts

3. **Week 3:** Deploy VictoriaMetrics
   - Create `composition-victoriametrics` role
   - Deploy to host-storage
   - Configure scrape targets
   - Verify data ingestion

4. **Week 4:** Validation and documentation
   - Run test queries
   - Document query patterns
   - Create operational runbook

## Resource Requirements

**Per ZFS Host (5 hosts):**
- zfs-api container: ~50MB RAM, negligible CPU (already deployed)
- zfs-exporter container: ~30MB RAM, negligible CPU (new)
- Disk: ~100MB per host (application + config)

**VictoriaMetrics (host-storage):**
- Memory: ~200-500MB (depends on cardinality)
- CPU: Low, mostly idle with 60s scrape interval
- Disk: ~5-8GB/year estimated (compressed metrics)
  - 5 hosts × ~50 metrics each × 60s interval × 1 year
  - With compression: ~6-8GB/year

**Total Additional Load:**
- Network: ~1-2 KB/s (scraping every 60s)
- Storage: <12GB for 1 year retention
- Minimal impact on existing infrastructure

## Success Criteria

✅ **Phase 1 Complete:** ACHIEVED
- ✅ 5 ZFS hosts expose zfs-api endpoints
- ✅ All endpoints return valid JSON
- ✅ SSL/TLS working via Traefik

⏳ **Phase 2 Complete:**
- Exporter running on all 5 monitored hosts
- Prometheus metrics format correct
- Metrics updated every 60s

⏳ **Phase 3 Complete:**
- VictoriaMetrics ingesting metrics from all hosts
- vmui interface accessible
- Data persisted to disk

⏳ **Phase 4 Complete:**
- Can query historical pool capacity
- Can query snapshot compliance over time
- Can identify backup failures
- Can track storage growth trends

⏳ **Issue #140 Complete:**
- Long-term queryable storage implemented
- All ZFS metrics centrally collected
- Documentation complete
- (Visualization deferred to future work)

## Future Enhancements (Out of Scope)

These are explicitly deferred per issue requirements:

1. **Visualization:**
   - Grafana dashboard deployment
   - Pre-built dashboard templates
   - Visual trend analysis

2. **Alerting:**
   - Alertmanager integration
   - Alert rules for pool health
   - Snapshot compliance alerts
   - Backup failure notifications

3. **Advanced Features:**
   - Predictive capacity planning
   - Anomaly detection
   - Cross-pool comparison views
   - Historical playback

## Risks and Mitigations

**Risk:** VictoriaMetrics consumes too much storage
- **Mitigation:** Start with 6-month retention, adjust based on actual usage
- **Mitigation:** VictoriaMetrics compression is excellent (~3-10x)

**Risk:** Exporter impacts zfs-api performance
- **Mitigation:** Exporter caches responses for scrape interval
- **Mitigation:** zfs commands are read-only and lightweight

**Risk:** Network connectivity issues prevent scraping
- **Mitigation:** Prometheus/VM handles temporary failures gracefully
- **Mitigation:** Backfill gaps when connectivity restored

**Risk:** Schema changes break exporter
- **Mitigation:** Version pin exporter to zfs-api version
- **Mitigation:** Comprehensive testing before rollout

## Open Questions

1. Should we expose VictoriaMetrics UI via Traefik? (Currently planned: yes)
2. What specific compliance thresholds should we track? (Currently: use existing policy definitions)
3. Should we track ZFS ARC statistics? (Currently: out of scope, add later if needed)
4. Export backup logs to metrics? (Currently: no, logs accessible via API)
5. Add vm-awfulwoman-hetzner monitoring later? (Currently: deferred)

## References

- **Issue:** #140
- **Related Roles:**
  - `composition-zfs-api` (existing)
  - `system-zfs-policy` (existing)
  - `backups-zfs-*` (existing)
- **Documentation:**
  - VictoriaMetrics: https://docs.victoriametrics.com/
  - Prometheus Exposition Format: https://prometheus.io/docs/instrumenting/exposition_formats/
  - PromQL: https://prometheus.io/docs/prometheus/latest/querying/basics/
