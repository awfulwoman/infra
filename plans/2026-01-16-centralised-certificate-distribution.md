# Plan: Centralized Wildcard Certificate Management (Issue #127)

## Goal

Replace per-host certificate requests with centralized wildcard
certificates distributed via NFS/rsync.

## Decisions

- **Domains:** Single wildcard for primary domain (`*.domain.com` +
  `domain.com`)
- **DNS Provider:** Hetzner (requires updating infra-certbot from
  DigitalOcean)
- **Remote Distribution:** rsync over Tailscale for hosts that can't
  use NFS

## Current State

- **6 Traefik hosts** each request their own per-domain certificates
  via DNS-01
- **infra-certbot role** exists on DNS host with `/fastpool/acme/`
  storage (uses DigitalOcean)
- **NFS infrastructure** exists (server-nfs, client-nfs roles)
- **Tailscale VPN** connects all hosts (100.64.0.0/10)

## Architecture

```text
DNS Host (Pi)                    host-storage
+-----------------+              +------------------+
| infra-certbot   |   rsync      | NFS server       |
| Request certs   | -----------> | /fastpool/certs  |
| /fastpool/acme  |              +--------+---------+
+-----------------+                       |
                              +-----------+-----------+
                              |           |           |
                            NFS         NFS        rsync
                              |           |           |
                              v           v           v
                    host-homeassistant  host-storage  remote hosts
                                                      (albion, VMs)
```

## Implementation Phases

### Phase 1: Configure Wildcard Certificate Request

Files: `ansible/roles/infra-certbot/`

1. Switch DNS provider from DigitalOcean to Hetzner
   - Update `dns01.yaml` tasks to use Hetzner API instead of
     `community.digitalocean`
   - Use `vault_hetzner_api_key_rw` (already exists in vault)
   - Hetzner API for DNS records: `https://dns.hetzner.com/api/v1/`
2. Update defaults to request wildcard: `*.{{ domain }}` and root
   `{{ domain }}`
3. Switch from staging to production ACME endpoint
4. Create bundled output (fullchain + key) for Traefik consumption

### Phase 2: Certificate Distribution Server

Files: New role `server-certificates` on host-storage

1. Create ZFS dataset `fastpool/certificates` (critical importance)
2. Export via NFS (read-only to Tailscale network)
3. Ansible task to sync certs from DNS host to storage server

### Phase 3: Certificate Clients

**Local hosts (NFS):** `client-certificates-nfs` role
- Mount `/fastpool/certificates` from host-storage
- Pattern: existing `client-nfs` role

**Remote hosts (rsync):** `client-certificates-rsync` role
- Pull certs via rsync over Tailscale SSH
- Systemd timer for daily sync
- Post-sync hook to reload Traefik

### Phase 4: Modify Traefik Configuration

Files: `ansible/roles/composition-reverseproxy/`

1. Add `reverseproxy_use_file_certs` option
2. Update `traefik-config.yaml.j2` for file-based TLS:

   ```yaml
   tls:
     certificates:
       - certFile: /certs/fullchain.crt
         keyFile: /certs/privkey.key
   ```

3. Update `docker-compose.yaml.j2` to mount certificate directory
4. Remove `certresolver: letsencrypt` from provider templates when
   using file certs

### Phase 5: Host Configuration Updates

| Host | Method | Config Changes |
|------|--------|----------------|
| dns | Local | Certs already at `/fastpool/acme/`, mount into Traefik |
| host-storage | Local | Certs synced to `/fastpool/certificates/` |
| host-homeassistant | NFS | Mount `/fastpool/certificates` from host-storage |
| host-albion | rsync | Daily pull from host-storage over Tailscale |
| vm-awfulwoman-hetzner | rsync | Daily pull from host-storage over Tailscale |
| vm-awfulwoman (DO) | rsync | Daily pull from host-storage over Tailscale |

### Phase 6: Renewal Automation

- Traefik watches certificate files for changes (built-in)
- Remote hosts: systemd timer syncs daily, sends HUP to Traefik
- Consider healthchecks.io monitoring for certificate expiry

## New Roles

| Role | Purpose |
|------|---------|
| `server-certificates` | Export certs via NFS from host-storage |
| `client-certificates-nfs` | Mount certs for local hosts |
| `client-certificates-rsync` | Sync certs for remote hosts |

## Critical Files to Modify

- `ansible/roles/infra-certbot/defaults/main.yaml`
- `ansible/roles/composition-reverseproxy/templates/traefik-config.yaml.j2`
- `ansible/roles/composition-reverseproxy/templates/docker-compose.yaml.j2`
- `ansible/inventory/host_vars/*/core.yaml` (each Traefik host)

## Verification

1. Test Hetzner DNS API integration in infra-certbot (staging)
2. Request staging wildcard cert on DNS host
3. Sync to host-storage, verify NFS export
4. Mount on host-homeassistant, verify Traefik uses wildcard cert
5. Test rsync to host-albion over Tailscale
6. Switch to production ACME, verify real cert
7. Test renewal flow end-to-end
8. Monitor via healthchecks.io for certificate expiry warnings
