# Implementation Plan: Grafana for ZFS Metrics Visualization

**Date:** 2026-01-25
**Related:** GH #140 (ZFS Monitoring) - Phase 4
**Status:** Planning

## Overview

Deploy Grafana as a Docker Compose application to visualize ZFS metrics collected by VictoriaMetrics. Create dashboards for pool capacity, dataset usage, snapshot compliance, and backup status across all monitored ZFS hosts.

## Current State

### What Exists
- ✅ VictoriaMetrics running on host-storage
- ✅ Scraping 5 ZFS hosts every 60s (host-storage, host-homeassistant, dns, host-backups, host-albion)
- ✅ 12 ZFS metric types exposed via zfs-api `/metrics` endpoint
- ✅ vmui web interface at `zfs.metrics.{{ domain_name }}`
- ✅ 1-year metric retention
- ✅ Data stored in `/slowpool/shared/metrics/zfs`

### What's Missing
- ❌ No Grafana composition
- ❌ No pre-configured datasource for VictoriaMetrics
- ❌ No ZFS-specific dashboards
- ❌ No dashboard provisioning automation

## Architecture

**Deployment Location:** host-storage (same host as VictoriaMetrics)

**Components:**
- Grafana container (grafana/grafana-oss:latest)
- Pre-configured VictoriaMetrics datasource
- Provisioned ZFS dashboards (JSON)
- Traefik integration for HTTPS access

**Network:**
- Same Docker network as VictoriaMetrics (`{{ default_docker_network }}`)
- VictoriaMetrics access: HTTPS via Traefik at `https://zfs.metrics.{{ domain_name }}`
- Grafana external access: HTTPS via Traefik at `https://grafana.{{ domain_name }}`

## Implementation Steps

### 1. Create composition-grafana Role

**Structure:**
```
ansible/roles/composition-grafana/
├── README.md
├── defaults/main.yaml
├── meta/main.yaml
├── tasks/main.yaml
├── templates/
│   ├── docker-compose.yaml.j2
│   ├── environment_vars.j2
│   └── provisioning/
│       ├── datasources.yaml.j2
│       └── dashboards.yaml.j2
└── files/
    └── dashboards/
        └── zfs-overview.json
```

**Key Variables (defaults/main.yaml):**
```yaml
composition_name: grafana
composition_grafana_enabled: true
composition_grafana_port: 3000
composition_grafana_container_name: "grafana"
composition_grafana_subdomain: "grafana"
composition_grafana_traefik_enabled: true

# VictoriaMetrics datasource
composition_grafana_victoriametrics_url: "https://zfs.metrics.{{ domain_name }}"
composition_grafana_victoriametrics_name: "VictoriaMetrics"

# Admin credentials (vault-encrypted)
composition_grafana_admin_user: "{{ vault_grafana_admin_user }}"
composition_grafana_admin_password: "{{ vault_grafana_admin_password }}"

# Dashboard settings
composition_grafana_dashboards_enabled: true
composition_grafana_default_theme: "dark"
```

**Docker Compose (docker-compose.yaml.j2):**
```yaml
name: "{{ composition_name }}"
services:
  grafana:
    image: grafana/grafana-oss:latest
    container_name: {{ composition_grafana_container_name }}
    restart: unless-stopped
    user: "{{ ansible_user_uid }}:{{ ansible_user_gid }}"
    ports:
      - "{{ composition_grafana_port }}:3000"
    volumes:
      - "{{ composition_config }}/data:/var/lib/grafana"
      - "{{ composition_config }}/provisioning:/etc/grafana/provisioning"
    env_file: .environment_vars
    networks:
      - "{{ default_docker_network }}"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ composition_grafana_container_name }}.rule=Host(`{{ composition_grafana_subdomain }}.{{ domain_name }}`)"
      - "traefik.http.routers.{{ composition_grafana_container_name }}.tls=true"
      - "traefik.http.routers.{{ composition_grafana_container_name }}.tls.certresolver=letsencrypt"
      - "traefik.http.services.{{ composition_grafana_container_name }}.loadbalancer.server.port={{ composition_grafana_port }}"

networks:
  "{{ default_docker_network }}":
    external: true
```

**Environment Variables (environment_vars.j2):**
```bash
# Admin credentials
GF_SECURITY_ADMIN_USER={{ composition_grafana_admin_user }}
GF_SECURITY_ADMIN_PASSWORD={{ composition_grafana_admin_password }}

# Server settings
GF_SERVER_ROOT_URL=https://{{ composition_grafana_subdomain }}.{{ domain_name }}
GF_SERVER_SERVE_FROM_SUB_PATH=false

# UI preferences
GF_USERS_DEFAULT_THEME={{ composition_grafana_default_theme }}

# Disable telemetry
GF_ANALYTICS_REPORTING_ENABLED=false
GF_ANALYTICS_CHECK_FOR_UPDATES=false

# Security
GF_SECURITY_DISABLE_GRAVATAR=true
GF_SNAPSHOTS_EXTERNAL_ENABLED=false
```

**Datasource Provisioning (provisioning/datasources.yaml.j2):**
```yaml
apiVersion: 1

datasources:
  - name: {{ composition_grafana_victoriametrics_name }}
    type: prometheus
    access: proxy
    url: {{ composition_grafana_victoriametrics_url }}
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "60s"
      httpMethod: POST
      tlsSkipVerify: false
```

**Dashboard Provisioning (provisioning/dashboards.yaml.j2):**
```yaml
apiVersion: 1

providers:
  - name: 'ZFS Dashboards'
    orgId: 1
    folder: 'ZFS'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

**Tasks (tasks/main.yaml):**
```yaml
# Standard composition tasks
- name: "Create compose file"
  ansible.builtin.template:
    src: docker-compose.yaml.j2
    dest: "{{ composition_root }}/docker-compose.yaml"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

- name: "Create .env file"
  ansible.builtin.template:
    src: environment_vars.j2
    dest: "{{ composition_root }}/.environment_vars"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

# Create directory structure
- name: Create directories
  become: true
  ansible.builtin.file:
    path: "{{ composition_config }}/{{ dir_item }}"
    state: directory
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"
  loop_control:
    loop_var: dir_item
  loop:
    - data
    - provisioning/datasources
    - provisioning/dashboards

# Provision datasources
- name: "Provision VictoriaMetrics datasource"
  ansible.builtin.template:
    src: provisioning/datasources.yaml.j2
    dest: "{{ composition_config }}/provisioning/datasources/victoriametrics.yaml"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

# Provision dashboard config
- name: "Provision dashboard configuration"
  ansible.builtin.template:
    src: provisioning/dashboards.yaml.j2
    dest: "{{ composition_config }}/provisioning/dashboards/default.yaml"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

# Copy dashboard JSON files
- name: "Copy ZFS dashboard"
  ansible.builtin.copy:
    src: dashboards/zfs-overview.json
    dest: "{{ composition_config }}/provisioning/dashboards/zfs-overview.json"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

# DNS registration
- name: Run Configure DNS role
  ansible.builtin.include_role:
    name: "network-register-subdomain"
  vars:
    configure_dns_subdomains:
      - "{{ composition_grafana_subdomain }}"

# Start composition
- name: Start Docker Compose project
  community.docker.docker_compose_v2:
    project_src: "{{ composition_root }}"
    state: present
    build: always
    remove_orphans: true
```

### 2. Create ZFS Overview Dashboard

**Dashboard JSON (files/dashboards/zfs-overview.json):**

Key panels to include:
1. **Pool Capacity Overview**
   - Gauge panels showing capacity % for each pool
   - Query: `zfs_pool_capacity{}`
   - Thresholds: green <70%, yellow 70-85%, red >85%

2. **Pool Health Status**
   - Stat panels showing health state
   - Query: `zfs_pool_health{}`
   - Color: green=ONLINE, red=DEGRADED/FAULTED

3. **Top 10 Datasets by Space Usage**
   - Bar chart
   - Query: `topk(10, zfs_dataset_used_bytes{})`
   - Human-readable units (GB/TB)

4. **Snapshot Compliance by Policy**
   - Table showing compliance % for each policy type
   - Query: `zfs_snapshot_compliance_percentage{}`
   - Rows: policy (critical/important/standard)
   - Color: green >95%, yellow 80-95%, red <80%

5. **Snapshot Count Trends**
   - Time series graph
   - Query: `zfs_snapshot_count{}`
   - Group by: hostname, policy

6. **Pool Fragmentation**
   - Gauge panels per pool
   - Query: `zfs_pool_fragmentation{}`
   - Thresholds: green <30%, yellow 30-50%, red >50%

7. **Dataset Space by Host**
   - Stacked area chart
   - Query: `sum by (hostname) (zfs_dataset_used_bytes{})`
   - 24h time range

8. **Backup Status Overview**
   - Stat panels (if backup metrics exist)
   - Last successful backup timestamp
   - Failed backup count

**Dashboard Settings:**
- Title: "ZFS Overview"
- Tags: ["zfs", "storage", "monitoring"]
- Refresh: 1m
- Time range: Last 24h (default)
- Templating variables:
  - `$hostname` - Filter by host
  - `$pool` - Filter by pool
  - `$policy` - Filter by snapshot policy

### 3. Ansible Playbook Integration

**Update:** `ansible/playbooks/baremetal/host-storage/victoriametrics.yaml`

Add Grafana role after VictoriaMetrics:
```yaml
- name: Storage NAS - VictoriaMetrics & Grafana
  hosts: host-storage
  vars:
    compositions:
      - victoriametrics
      - grafana
  roles:
    # ... existing roles ...
    - role: composition-victoriametrics
    - role: composition-grafana
    # ... other roles ...
```

Alternatively, create dedicated playbook:
**New:** `ansible/playbooks/baremetal/host-storage/grafana.yaml`

### 4. Vault Configuration

**Add to Ansible Vault:**
```yaml
vault_grafana_admin_user: "admin"
vault_grafana_admin_password: "<secure-password>"
```

Store in appropriate vault file (likely `group_vars/all/vault.yaml`)

### 5. DNS Registration

Via `network-register-subdomain` role (already integrated in tasks)
- Subdomain: `grafana.{{ domain_name }}`
- Points to: host-storage IP

### 6. Testing & Verification

**Deployment Test:**
```bash
# Deploy Grafana
ansible-playbook ansible/playbooks/baremetal/host-storage/victoriametrics.yaml

# Verify container running
ssh host-storage 'docker ps | grep grafana'

# Check logs
ssh host-storage 'docker logs grafana'

# Test datasource connectivity
curl -s https://grafana.{{ domain_name }}/api/health | jq
```

**Dashboard Verification:**
1. Access https://grafana.{{ domain_name }}
2. Login with vault credentials
3. Navigate to "ZFS Overview" dashboard
4. Verify all panels load data
5. Test variable dropdowns ($hostname, $pool, $policy)
6. Verify time range selector works
7. Test panel refresh intervals

**Metric Query Tests:**
```promql
# Verify metrics are queryable
zfs_pool_capacity{}
zfs_pool_health{}
zfs_dataset_used_bytes{}
zfs_snapshot_count{}
zfs_snapshot_compliance_percentage{}
```

## Dependencies

**Role Dependencies (meta/main.yaml):**
```yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: grafana
```

**External Dependencies:**
- VictoriaMetrics must be running and accessible at `https://zfs.metrics.{{ domain_name }}`
- Docker network (`{{ default_docker_network }}`) for Traefik integration
- Traefik reverse proxy must be operational with valid TLS certificates

## Documentation

**README.md for composition-grafana:**
- Overview of Grafana deployment
- Access URL and default credentials location
- Dashboard descriptions
- How to add new dashboards
- How to modify datasource
- Troubleshooting guide

**Key Documentation Sections:**
1. Architecture & Integration
2. Dashboard Catalog
3. Query Examples
4. Adding Custom Dashboards
5. Performance Tuning
6. Backup & Restore

## Rollback Plan

If deployment fails:
```bash
# Stop Grafana
ssh host-storage 'cd /opt/compositions/grafana && docker compose down'

# Remove from playbook
# Revert playbook changes

# DNS cleanup (if needed)
# Remove grafana subdomain registration
```

## Success Criteria

- [ ] Grafana accessible at https://grafana.{{ domain_name }}
- [ ] VictoriaMetrics datasource auto-configured
- [ ] ZFS Overview dashboard loads successfully
- [ ] All panels display metrics from 5+ hosts
- [ ] Variable filters work ($hostname, $pool, $policy)
- [ ] Traefik HTTPS certificates provisioned
- [ ] No errors in Grafana logs
- [ ] Dashboard refresh works without errors
- [ ] Documentation complete in README

## Timeline Estimate

- Role structure & templates: 1h
- Dashboard JSON creation: 2h
- Testing & refinement: 1h
- Documentation: 30m

**Total:** ~4.5 hours

## Future Enhancements (Out of Scope)

- Additional dashboards (detailed pool view, backup deep-dive)
- Alerting rules integration
- Grafana user management & RBAC
- Dashboard export/import automation
- Custom Grafana plugins
- Long-term dashboard versioning

## Unresolved Questions

1. Admin password generation strategy? (manual vault entry vs auto-generated)
2. Additional datasources needed? (node_exporter, cadvisor, etc.)
3. Dashboard permissions - read-only default or editable?
4. Multiple dashboards or single comprehensive view?
5. Panel auto-refresh intervals - 1m sufficient?
6. Retention for Grafana config/dashboards - backup strategy?
