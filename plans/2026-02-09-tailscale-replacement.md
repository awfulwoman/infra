# Plan: Replace Tailscale with Self-Hosted Alternative

**Issue:** #75 - Implement WireGuard directly as an alternative to Tailscale
**Date:** 2026-02-08
**Status:** Planning

## Problem Statement

Tailscale is currently used across all infrastructure hosts for mesh networking, but
presents vendor lock-in concerns. Need self-hosted alternative that:

- Works behind CGNAT (home hosts)
- Provides mesh or hub-spoke topology
- Removes dependency on Tailscale Inc.
- Maintains current functionality

## Current State

### Tailscale Usage
- Deployed via `artis3n.tailscale` Galaxy role
- Used on ~13 infrastructure hosts
- Handles NAT traversal via DERP servers
- Provides mesh networking
- Documented in `docs/bastardtech.md` as "uncomfortable dependency"

### Infrastructure Topology
```
Home (CGNAT):
- host-storage, host-homeassistant, dns, belinda, host-backups

Cloud (Public IP):
- vm-awfulwoman-hetzner (188.245.37.81)

Remote/Offsite:
- host-albion, vm-claude-dev, vm-homeautomation, vm-downloads, vm-media

Personal:
- host-mba2011
```

### CGNAT Challenge
- Home hosts can't accept direct inbound connections
- Need NAT traversal or relay mechanism
- Plain WireGuard insufficient without coordination

## Options Analysis

### Option 1: WireGuard + VPS Relay

**Architecture:** Hub-and-spoke with Hetzner VM as relay

**Pros:**
- Simple, minimal moving parts
- Full control over all components
- Already have suitable VPS (vm-awfulwoman-hetzner)
- Pure WireGuard (well-audited)
- Cheap (~€5/mo existing infrastructure)

**Cons:**
- Single point of failure (relay down = VPN down)
- All traffic routes through relay (performance bottleneck)
- No automatic peer discovery
- Manual key management
- No mesh topology (hub-spoke only)

**Implementation Time:** 10-15 hours

**Roles:**
- `network-wireguard-relay` - relay server
- `network-wireguard-client` - all peers

---

### Option 2: Nebula

**Architecture:** Self-hosted lighthouse servers + mesh network

**Pros:**
- Battle-tested (50k+ hosts at Slack)
- Full self-hosting, zero external dependencies
- Certificate-based identity (cleaner than keys)
- Mesh topology with automatic peer discovery
- Group-based firewall rules built-in
- Proven at massive scale

**Cons:**
- Not WireGuard (uses Noise Protocol Framework)
- Lighthouse servers required (need public IPs)
- Certificate lifecycle management
- Smaller ecosystem than WireGuard
- Learning curve for new concepts

**Implementation Time:** 15-19 hours

**Roles:**
- `network-nebula-ca` - CA management
- `network-nebula-lighthouse` - coordination servers
- `network-nebula-client` - all peers

---

### Option 3: Headscale

**Architecture:** Self-hosted Tailscale control server + Tailscale clients

**Pros:**
- Uses actual Tailscale clients (familiar UX)
- WireGuard protocol under the hood
- Self-hosted coordination (no vendor dependency)
- Mesh topology
- Optional web UI
- Can migrate back to Tailscale if needed
- Good documentation and community

**Cons:**
- Headscale features lag behind Tailscale
- Still uses Tailscale client binaries
- Requires trust in Tailscale client code

**Implementation Time:** 6-8 hours

**Roles:**
- `network-headscale-server` - control server
- `network-headscale-client` - all peers

---

### Option 4: Innernet

**Architecture:** CIDR tree-based mesh with innernet server

**Pros:**
- Pure WireGuard implementation
- Unique CIDR-based organization (familiar networking concepts)
- Security via subnet visibility (compromised peer sees limited network)
- Simple architecture (Rust + SQLite)
- Self-hosted, no external dependencies
- Lightweight and performant

**Cons:**
- No web UI (CLI only)
- Smaller community, less documentation
- Manual invitation file transfer
- Requires upfront CIDR planning
- Less mature than alternatives
- CIDR restructure = painful migration

**Implementation Time:** 11-15 hours

**Roles:**
- `network-innernet-server` - coordination server
- `network-innernet-admin` - CIDR structure management
- `network-innernet-client` - all peers

---

## Comparison Matrix

| Feature | WG+Relay | Nebula | Headscale | Innernet |
|---------|----------|--------|-----------|----------|
| **Protocol** | WireGuard | Noise | WireGuard | WireGuard |
| **Mesh** | No (hub-spoke) | Yes | Yes | Coordinated |
| **Self-hosted** | Yes | Yes | Yes | Yes |
| **UI** | No | No | Optional | No |
| **CGNAT** | Good | Good | Excellent | Good |
| **Complexity** | Low | Medium | Low | Medium |
| **Maturity** | N/A (custom) | Very High | High | Medium |
| **Setup time** | 10-15h | 15-19h | 6-8h | 11-15h |
| **Community** | N/A | Medium | Large | Small |
| **Vendor risk** | None | None | Low | None |

## Recommended Approach

### Primary Recommendation: Headscale

**Rationale:**
- Fastest implementation (6-8 hours)
- WireGuard protocol (meets issue requirement)
- Familiar UX (Tailscale clients)
- Self-hosted control server (removes vendor lock-in)
- Largest community support
- Mesh topology maintained
- Can fall back to Tailscale if needed

**Trade-offs:**
- Still uses Tailscale client binaries (some trust required)
- Headscale features lag official Tailscale

### Alternative Recommendation: Innernet

**When to choose:**
- Want pure WireGuard without wrappers
- Love CIDR-based organization model
- Comfortable with CLI-only tools
- Network structure maps to security boundaries
- Willing to invest 11-15 hours

**Trade-offs:**
- Steeper learning curve
- Less documentation
- Manual operations (invitation files)

### Not Recommended: WireGuard + VPS Relay

**Why not:**
- Single point of failure
- Performance bottleneck (all traffic via relay)
- No mesh topology
- Similar complexity to Headscale but fewer benefits

### Not Recommended (Initially): Nebula

**Why not:**
- Doesn't use WireGuard (issue specifically asks for WireGuard)
- Longest implementation time
- Learning new protocol + concepts

**Consider later if:**
- Headscale proves insufficient
- Want to move away from Tailscale ecosystem entirely
- Need advanced group-based firewall features

## Implementation Plan (Headscale)

### Phase 1: Server Setup (2-3 hours)

**Tasks:**
1. Create `network-headscale-server` role
2. Deploy to vm-awfulwoman-hetzner
3. Install Headscale binary
4. Configure headscale.yaml
5. Set up systemd service
6. Configure DNS (headscale.internal.domain)
7. Optional: deploy headscale-ui

**Deliverables:**
- Running Headscale server on vm-awfulwoman-hetzner
- Web UI accessible (optional)
- Ready to accept client connections

### Phase 2: Client Role Development (2-3 hours)

**Tasks:**
1. Create `network-headscale-client` role
2. Install Tailscale client package
3. Configure control server URL
4. Generate pre-auth keys via Headscale API
5. Template systemd service configuration
6. Add firewall rules

**Deliverables:**
- Reusable client role
- Automated join process
- Systemd integration

### Phase 3: ACL Configuration (1-2 hours)

**Tasks:**
1. Design ACL policy matching current Tailscale setup
2. Map Ansible groups to Headscale groups
3. Configure SSH access rules
4. Set up service-specific rules (ZFS backups, etc.)

**Example ACL:**
```json
{
  "groups": {
    "group:admin": ["host-mba2011"],
    "group:zfs-backup-servers": ["host-backups", "belinda"],
    "group:zfs-backup-clients": ["host-storage", "host-homeassistant", "dns"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["group:admin"],
      "dst": ["*:22"]
    },
    {
      "action": "accept",
      "src": ["group:zfs-backup-servers"],
      "dst": ["group:zfs-backup-clients:22"]
    }
  ]
}
```

**Deliverables:**
- ACL policy file
- Group definitions
- Service access rules

### Phase 4: Pilot Deployment (1-2 hours)

**Tasks:**
1. Deploy to 2 test hosts (e.g., dns + host-storage)
2. Verify connectivity
3. Test service access
4. Monitor for issues
5. Validate performance

**Success Criteria:**
- Hosts can ping each other
- SSH works between hosts
- Services accessible (ZFS, etc.)
- No connection drops over 24 hours

### Phase 5: Full Rollout (1-2 hours)

**Tasks:**
1. Deploy client role to all remaining hosts
2. Verify all hosts appear in Headscale
3. Test mesh connectivity
4. Update documentation
5. Keep Tailscale running (parallel)

**Deliverables:**
- All hosts on Headscale network
- Connectivity matrix validated
- Runbook for operations

### Phase 6: Migration & Cleanup (1 hour)

**Tasks:**
1. Update DNS/service configs to use Headscale IPs
2. Monitor for 1 week
3. Disable Tailscale systemd services
4. Remove artis3n.tailscale role from bootstrap
5. Update documentation
6. Close GH issue #75

**Rollback Plan:**
- Tailscale still installed
- `systemctl start tailscaled` on each host
- Re-enable in bootstrap role
- Back to working state in <5 minutes

## Migration Strategy

### Week 1: Setup & Testing
- Deploy Headscale server
- Test with 2 hosts
- Validate functionality

### Week 2: Rollout
- Deploy to all hosts
- Run parallel with Tailscale
- Monitor stability

### Week 3: Validation
- Full connectivity testing
- Service verification
- Performance benchmarking

### Week 4: Cutover
- Update service configs
- Disable Tailscale
- Document for future

### Rollback Triggers
- Connection failures >5% of hosts
- Performance degradation >20%
- Service disruption >1 hour
- ACL issues blocking critical access

## Resource Requirements

### Infrastructure
- vm-awfulwoman-hetzner (already have)
  - +100MB disk for Headscale
  - +50MB RAM
  - UDP port 41641 (DERP relay)
  - TCP port 8080 (control server)

### Time Investment
- Implementation: 6-8 hours
- Testing: 2-3 hours
- Documentation: 1 hour
- **Total: 9-12 hours**

### Skills Needed
- Ansible role development ✓
- WireGuard concepts ✓
- Systemd service management ✓
- JSON ACL configuration (new, but simple)

## Success Criteria

### Technical
- [ ] All hosts connected to Headscale
- [ ] Mesh connectivity functional
- [ ] Services accessible (SSH, ZFS, etc.)
- [ ] Performance within 10% of Tailscale
- [ ] No connection drops for 7 days

### Operational
- [ ] ACLs enforce desired access control
- [ ] Monitoring/alerting configured
- [ ] Runbook documented
- [ ] Team trained on operations
- [ ] Rollback tested and verified

### Strategic
- [ ] No vendor lock-in to Tailscale Inc.
- [ ] Self-hosted control plane
- [ ] WireGuard protocol in use
- [ ] Cost reduced (free vs potential paid Tailscale)

## Risks & Mitigation

### Risk: Headscale server failure
**Impact:** Loss of mesh network, new peers can't join
**Mitigation:**
- Keep Tailscale installed as fallback
- Monitor Headscale health
- Automated backups of Headscale DB
- Document fast recovery procedure

### Risk: ACL misconfiguration
**Impact:** Service disruption, blocked access
**Mitigation:**
- Test ACLs in staging first
- Default-allow policy during migration
- Admin override capability
- Quick rollback to Tailscale

### Risk: Performance issues
**Impact:** Slow connections, service degradation
**Mitigation:**
- Benchmark before migration
- Monitor latency/throughput
- DERP relay on same Hetzner VM (low latency)
- Gradual rollout to detect issues early

### Risk: Client compatibility
**Impact:** Some hosts can't connect
**Mitigation:**
- Test on each OS version first
- Tailscale client widely supported
- Fallback to Tailscale if needed

## Future Enhancements

### Short-term (Post-Migration)
- Set up Prometheus monitoring for Headscale
- Automate ACL updates via Ansible
- Deploy headscale-ui for visibility
- Create alerting for disconnected peers

### Long-term (6+ months)
- Evaluate Nebula for comparison
- Consider multi-region DERP relays
- Implement key rotation automation
- Explore Headscale HA setup

## Open Questions

1. **ACL Granularity:** How detailed should ACL rules be?
   - Start simple (SSH + service-specific) or comprehensive?

2. **DERP Relay:** Run own DERP relay or use Headscale's embedded?
   - Own relay = more control, more complexity
   - Embedded = simpler, less flexible

3. **Monitoring:** What metrics are critical to monitor?
   - Peer count, connection quality, bandwidth?

4. **Backup Strategy:** How often backup Headscale DB?
   - Daily via ZFS snapshots? Real-time replication?

5. **Second Server:** Deploy redundant Headscale server?
   - On dns or belinda for HA?
   - Worth complexity for ~13 hosts?

6. **Migration Window:** Parallel run time before cutover?
   - 1 week sufficient or need longer validation?

7. **Documentation:** Level of detail for runbook?
   - Basic ops or comprehensive troubleshooting guide?

## Alternative: Innernet (If Choosing This Path)

### CIDR Structure Design
```
10.200.0.0/16  (root - "infra")
├─ 10.200.0.0/24   (infra - server + admin)
├─ 10.200.1.0/24   (home-baremetal)
├─ 10.200.2.0/24   (home-vms)
├─ 10.200.3.0/24   (cloud)
├─ 10.200.4.0/24   (backup-servers)
└─ 10.200.5.0/24   (admin-devices)
```

### Implementation Differences
- Phase 1: Server + CIDR design (3-4 hours)
- Phase 2: Generate invitations (2 hours)
- Phase 3: Client role (3-4 hours)
- Phase 4: Testing (2-3 hours)
- **Total: 11-15 hours**

### CIDR Associations
```bash
# Allow backup servers to reach storage hosts
inn add-association home-baremetal backup-servers

# Allow admin devices to reach everything
inn add-association admin-devices home-baremetal
inn add-association admin-devices home-vms
inn add-association admin-devices cloud
inn add-association admin-devices backup-servers
```

## Appendix: Command Reference

### Headscale Operations
```bash
# List peers
headscale nodes list

# Create pre-auth key
headscale preauthkeys create --expiration 24h

# View ACLs
headscale policy get

# Debug peer
headscale nodes show <node-id>
```

### Innernet Operations
```bash
# List visible peers
inn list infra

# Add new peer
inn add-peer infra <name> --cidr <cidr-name>

# Update peer list
inn fetch infra

# Show network tree
inn show infra
```

### Rollback Commands
```bash
# Disable Headscale/Innernet
systemctl stop headscale@infra  # or innernet@infra

# Re-enable Tailscale
systemctl start tailscaled
tailscale up
```

## Conclusion

**Recommended:** Headscale for fastest, lowest-risk migration

**Timeline:** 2-4 weeks from start to Tailscale removal

**Next Steps:**
1. Review plan with stakeholders
2. Schedule implementation window
3. Create Ansible roles
4. Begin Phase 1 (server setup)

**Approval Required:**
- [ ] Technical approach approved
- [ ] Timeline acceptable
- [ ] Resource allocation confirmed
- [ ] Rollback plan reviewed
