# Loki Log Aggregation Implementation Plan

## Executive Summary

Add centralized log aggregation to the infrastructure using Grafana Loki + Promtail, following established composition-* role patterns. Loki will be deployed on host-storage (alongside Grafana/VictoriaMetrics), with Promtail agents on all Docker-enabled hosts collecting container and system logs.

**Key Metrics:**
- **Hosts**: 7 Docker-enabled hosts
- **Containers**: ~40 across infrastructure
- **Storage**: ~7GB for 30-day retention
- **Log volume**: ~230MB/day compressed

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        host-storage                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Grafana    │  │ VictoriaMetrics│  │       Loki         │  │
│  │ (existing)   │  │  (existing)    │  │   (NEW)            │  │
│  │   :3000      │  │    :8428       │  │   :3100            │  │
│  └──────┬───────┘  └────────────────┘  └─────────▲──────────┘  │
│         │                                         │             │
│         └─────────────[queries]───────────────────┘             │
│                                                                 │
│  Storage: /slowpool/shared/logs/loki (retention: 30d)          │
└─────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │ HTTPS via Tailscale
                                 │ (loki.{{ domain_name }})\n                                 │
         ┌───────────────────────┴───────────────────────┐
         │                       │                       │
    ┌────┴────┐            ┌─────┴─────┐         ┌──────┴──────┐
    │ Promtail│            │ Promtail  │         │  Promtail   │
    │  host-  │            │   dns     │         │   host-     │
    │homeass. │            │  :9080    │         │   backups   │
    │ :9080   │            └───────────┘         │   :9080     │
    └─────────┘                                  └─────────────┘
         │                       │                       │
    [Docker logs]           [Docker logs]          [Docker logs]
    [journald]              [journald]             [journald]
```

## Core Design Decisions

### 1. Loki Server Location
**Decision:** Deploy on host-storage as composition-loki

**Rationale:**
- Already hosts Grafana + VictoriaMetrics (centralized monitoring)
- Has fastpool (SSD) and slowpool (HDD) for storage tiering
- Adequate resources for log aggregation

### 2. Promtail Deployment
**Decision:** Systemd service (NOT Docker container)

**Rationale:**
- Needs root access to `/var/lib/docker/containers` for log files
- Requires journald access for system logs
- Avoids Docker-in-Docker complexity
- Survives Docker daemon restarts

### 3. Log Collection Strategy
**Decision:** Keep default JSON logging driver + Promtail scraping

**Rationale:**
- Non-invasive (no changes to 40+ docker-compose files)
- Local logs remain available via `docker logs`
- Centralized config management in Ansible
- Easy rollback if Loki fails

### 4. Storage Configuration
**Location:** `/slowpool/shared/logs/loki`
**Retention:** 30 days
**Estimated size:** ~7GB

**Rationale:**
- Logs are cold data (infrequent access) - HDD acceptable
- 30 days balances storage vs debugging needs
- ZFS compression (lz4) reduces storage by ~5x

### 5. Log Labeling Strategy
```yaml
labels:
  host: "{{ inventory_hostname }}"       # storage, dns, etc.
  job: "docker" | "systemd"              # Log source type
  composition: "<composition_name>"       # jellyfin, gitea, etc.
  container_name: "<container_name>"     # Actual container
  stream: "stdout" | "stderr"            # Output stream
```

## Implementation Roles

### Role 1: composition-loki

**Purpose:** Deploy Loki server on host-storage

**File Structure:**
```
ansible/roles/composition-loki/
├── defaults/main.yaml
├── meta/main.yaml
├── tasks/main.yaml
├── templates/
│   ├── docker-compose.yaml.j2
│   ├── environment_vars.j2
│   └── loki-config.yaml.j2
```

**Key Configuration Variables:**
```yaml
composition_name: loki
composition_loki_port: 3100
composition_loki_storage_path: "/slowpool/shared/logs/loki"
composition_loki_retention_period: "720h"  # 30 days
composition_loki_subdomain: "loki"
composition_loki_traefik_enabled: true
```

**Docker Compose Service:**
- Image: `grafana/loki:2.9.3`
- Ports: `3100:3100`
- Volumes: Config + data storage
- Network: `guineanet` (shared Docker network)
- Traefik labels for HTTPS access

**Loki Configuration Highlights:**
- Schema: boltdb-shipper + filesystem storage
- Retention: 30 days with automated compaction
- Ingestion limits: 64MB/s rate, 128MB burst
- Chunk idle period: 1h (balance memory vs disk)

### Role 2: system-promtail

**Purpose:** Deploy Promtail log shipper on all infra hosts

**File Structure:**
```
ansible/roles/system-promtail/
├── defaults/main.yaml
├── tasks/main.yaml
├── templates/
│   ├── promtail-config.yaml.j2
│   └── promtail.service.j2
└── handlers/main.yaml
```

**Key Configuration:**
```yaml
promtail_version: "2.9.3"
promtail_binary_path: "/usr/local/bin/promtail"
promtail_loki_url: "https://loki.{{ domain_name }}/loki/api/v1/push"
promtail_docker_log_path: "/var/lib/docker/containers"
promtail_journald_enabled: true
```

**Scrape Configs:**

1. **Docker Container Logs:**
   - Path: `/var/lib/docker/containers/*/*-json.log`
   - Labels extracted: composition, container_name, stream
   - Pipeline: JSON parsing → label extraction → output formatting

2. **System Journald Logs:**
   - Max age: 12h
   - Labels: unit, hostname, priority
   - Filters: All systemd units

**Systemd Service:**
- Runs as root (needs Docker socket access)
- Restart on failure with 10s delay
- Logs to journald

### Integration: Grafana Datasource

**Update:** `composition-grafana/templates/provisioning/datasources.yaml.j2`

Add Loki datasource alongside VictoriaMetrics:

```yaml
- name: Loki
  type: loki
  access: proxy
  uid: Loki
  url: https://loki.{{ domain_name }}
  isDefault: false
  editable: false
  jsonData:
    maxLines: 1000
```

## Deployment Sequence

### Phase 1: Prepare Storage (5 min)

1. **Add ZFS dataset to host-storage config:**

   File: `ansible/inventory/host_vars/host-storage/core.yaml`

   ```yaml
   zfs:
     slowpool:
       datasets:
         shared:
           datasets:
             logs:
               datasets:
                 loki:
                   policy: high
                   extra_zfs_properties:
                     compression: lz4
                     recordsize: 128K
   ```

2. **Create ZFS dataset:**
   ```bash
   ansible-playbook ansible/playbooks/baremetal/host-storage/zfs.yaml
   ```

### Phase 2: Deploy Loki Server (10 min)

3. **Create composition-loki role** (structure detailed above)

4. **Add to host-storage playbook:**

   File: `ansible/playbooks/baremetal/host-storage/core.yaml`

   Insert after `composition-victoriametrics`:
   ```yaml
   - role: composition-loki
   ```

5. **Deploy Loki:**
   ```bash
   ansible-playbook ansible/playbooks/baremetal/host-storage/compositions.yaml --tags loki
   ```

6. **Verify:**
   ```bash
   curl https://loki.{{ domain_name }}/ready
   # Expected: ready
   ```

### Phase 3: Deploy Promtail Agents (15 min)

7. **Create system-promtail role** (structure detailed above)

8. **Add to all Docker host playbooks:**
   - `playbooks/baremetal/host-storage/core.yaml`
   - `playbooks/baremetal/host-homeassistant/core.yaml`
   - `playbooks/baremetal/dns/core.yaml`
   - `playbooks/baremetal/host-backups/core.yaml`
   - `playbooks/baremetal/host-albion/core.yaml`
   - `playbooks/baremetal/belinda/core.yaml`
   - `playbooks/virtual/vm-awfulwoman-hetzner/core.yaml`

   Insert after `system-docker`:
   ```yaml
   - role: system-promtail
   ```

9. **Deploy incrementally (test on host-storage first):**
   ```bash
   # Test on host-storage
   ansible-playbook ansible/playbooks/baremetal/host-storage/core.yaml --tags promtail

   # Verify logs appear in Grafana
   # Then roll out to remaining hosts
   ansible-playbook ansible/playbooks/baremetal/host-homeassistant/core.yaml --tags promtail
   # ... etc
   ```

10. **Verify all agents:**
    ```bash
    ansible infra -m systemd -a "name=promtail state=started" --become
    ansible infra -m shell -a "journalctl -u promtail -n 10" --become
    ```

### Phase 4: Update Grafana Integration (5 min)

11. **Update datasources.yaml.j2** (add Loki datasource as shown above)

12. **Re-run Grafana role:**
    ```bash
    ansible-playbook ansible/playbooks/baremetal/host-storage/core.yaml --tags grafana
    ```

13. **Verify in Grafana UI:**
    - Navigate to Configuration → Data Sources
    - Confirm "Loki" datasource exists
    - Test connection

### Phase 5: Testing & Validation (10 min)

14. **Query logs in Grafana Explore:**
    - Select "Loki" datasource
    - Query: `{host="host-storage"}`
    - Verify logs appear

15. **Test log ingestion:**
    ```bash
    docker exec jellyfin echo "TEST_LOG_ENTRY_$(date +%s)"
    ```

    Search in Grafana:
    ```logql
    {composition="jellyfin"} |= "TEST_LOG_ENTRY"
    ```

16. **Verify multi-host collection:**
    ```logql
    sum by (host) (count_over_time({job="docker"}[5m]))
    ```
    Should show all 7 hosts

## Testing & Verification

### Pre-Deployment Checks

- [x] Verify Tailscale connectivity across all hosts
- [x] Check Docker log locations exist (`/var/lib/docker/containers`)
- [x] Confirm ZFS dataset can be created

### Post-Deployment Tests

**Loki Health:**
```bash
curl https://loki.{{ domain_name }}/ready
curl https://loki.{{ domain_name }}/metrics | grep loki_ingester_streams
```

**Promtail Status:**
```bash
ansible infra -m systemd -a "name=promtail status" --become
ansible infra -m shell -a "cat /var/lib/promtail/positions.yaml" --become
```

**Log Ingestion:**
- Generate test log in container
- Query via Loki API
- Verify in Grafana Explore

**Performance:**
- Query latency (<2s for 1h range)
- Storage growth (~230MB/day)
- Promtail memory usage (<100MB per host)

## LogQL Query Examples

**All logs from host-storage:**
```logql
{host="host-storage"}
```

**Jellyfin container logs:**
```logql
{composition="jellyfin"}
```

**All ZFS API logs (cross-host):**
```logql
{composition="zfs-api"}
```

**Error logs from all containers:**
```logql
{job="docker"} |= "error" or "ERROR"
```

**Systemd service failures:**
```logql
{job="systemd", unit="docker.service"} |= "failed"
```

**Rate of errors per composition:**
```logql
sum by (composition) (rate({job="docker"} |= "error" [5m]))
```

## Storage Estimates

**Assumptions:**
- 40 containers across 7 hosts
- 100 log lines/min per container average
- 200 bytes/line average
- ZFS lz4 compression: 5:1 ratio

**Calculations:**
```
Raw daily: 40 × 100 × 1440 × 200 bytes = 1.15 GB/day
Compressed: 1.15 GB ÷ 5 = 230 MB/day
30-day retention: 230 MB × 30 = ~7 GB total
```

**Recommendation:** Allocate 20GB for headroom and growth.

## Trade-offs & Rationale

| Decision | Alternative | Why Chosen |
|----------|-------------|------------|
| Single Loki instance | Distributed cluster | Homelab scale doesn't justify complexity; 100MB/day easily handled |
| Promtail systemd service | Promtail container | Needs Docker socket + journald; systemd avoids privilege issues |
| JSON logging driver | Loki Docker driver | Non-invasive; keeps local logs; centralized config |
| 30-day retention | 7/90 days | Balances storage vs debugging; adjustable via variable |
| slowpool storage | fastpool | Logs are cold data; HDDs acceptable; preserves SSD |
| Tailscale network | Direct IPs | Already in use; simplifies firewall rules |
| No authentication | BasicAuth | Private Tailscale network sufficient |

## Maintenance

### Daily Operations
- **No action required** - Logs auto-expire after 30 days
- Loki compactor runs every 10min

### Weekly Checks
- Verify Loki datasource health in Grafana
- Review Loki /metrics for compaction errors

### Monthly Tasks
- Check storage usage: `du -sh /slowpool/shared/logs/loki`
- Adjust retention if exceeding 15GB

### Troubleshooting

**Promtail not shipping logs:**
```bash
journalctl -u promtail -f
cat /var/lib/promtail/positions.yaml
```

**Loki ingestion errors:**
```bash
docker logs loki
curl https://loki.{{ domain_name }}/metrics | grep loki_ingester
```

**Missing logs from specific host:**
```bash
ssh <host> systemctl status promtail
ssh <host> cat /etc/promtail/promtail-config.yaml
```

## Rollback Plan

If Loki causes issues:

1. Stop Promtail agents:
   ```bash
   ansible infra -m systemd -a "name=promtail state=stopped enabled=false" --become
   ```

2. Remove Loki composition:
   ```bash
   ssh host-storage "cd /fastpool/compositions/loki && docker compose down"
   ```

3. Remove Grafana datasource (via UI or re-run Grafana role)

**No data loss** - Docker container logs remain in `/var/lib/docker/containers`

## Future Enhancements

**Phase 2 (Optional):**
1. Application-specific log parsing (Jellyfin playback, Gitea auth failures)
2. Alerting on log patterns (crashes, disk errors, auth failures)
3. Log-based metrics (error rates, HTTP requests from Traefik)
4. Long-term archive to S3-compatible storage (MinIO)

## Critical Files

**New Roles:**
- `ansible/roles/composition-loki/` - Complete role structure
- `ansible/roles/system-promtail/` - Complete role structure

**Modified Files:**
- `ansible/roles/composition-grafana/templates/provisioning/datasources.yaml.j2` - Add Loki datasource
- `ansible/roles/composition-grafana/defaults/main.yaml` - Add Loki URL variable
- `ansible/inventory/host_vars/host-storage/core.yaml` - Add ZFS dataset
- 7 host playbooks - Add system-promtail role

**Reference Files (patterns to follow):**
- `ansible/roles/composition-victoriametrics/tasks/main.yaml` - Composition pattern
- `ansible/roles/monitoring-linux2mqtt/templates/l2m.service` - Systemd service pattern

## Unresolved Questions

1. **Version pinning:** Use `latest` tag or pin to `2.9.3`?
   - **Recommendation:** Pin to 2.9.3 for stability

2. **Include testrouter/pikvm logs?**
   - Minimal containers, not critical initially
   - Can add later

3. **Scrape /var/log files?** (syslog, auth.log)
   - journald already covers most system logs
   - Add via scrape_configs if needed

4. **Loki authentication?**
   - Not needed for homelab (Tailscale provides security)
   - Consider if exposing externally

5. **Dashboard provisioning?**
   - Create log overview dashboard?
   - Or rely on ad-hoc Explore queries?

## Summary

This plan provides a complete, production-ready Loki log aggregation system following your established infrastructure patterns. The implementation is:

- **Non-invasive:** No changes to existing Docker configs
- **Scalable:** Handles current 40 containers with room for growth
- **Maintainable:** Automated retention, compression, compaction
- **Integrated:** Seamlessly works with existing Grafana setup
- **Reversible:** Clean rollback path if needed

**Estimated implementation time:** 2-3 hours (including testing)
