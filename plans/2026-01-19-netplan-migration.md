# Netplan Migration Implementation Plan

**Date**: 2026-01-19
**Issue**: #83
**Status**: Implemented & Tested

## Executive Summary

This plan outlines the migration from NetworkManager/nmcli-based network configuration to netplan for all Ubuntu servers. The approach replaces unused nmcli roles with a unified netplan-based system, leveraging existing patterns from the virtual-hetzner role and host_vars conventions.

## Current State Analysis

**Findings from codebase exploration:**
- nmcli-based roles (network-ip-address-static, network-ip-address-dhcp) are NOT actively used by any hosts
- Only host-albion uses network-ip-address-forwarding (sysctl-based, not nmcli)
- All bare-metal hosts define `host_ipv4` and `configure_dns_linkdevice_physical` in host_vars
- virtual-hetzner role already has netplan pattern established
- 8 hosts have static IPs defined (192.168.1.x range)
- No hosts explicitly configured for DHCP (dns and host-albion have empty host_ipv4)

## Design Decisions

### 1. Replace vs Create New Roles
**Decision**: Replace existing roles

**Rationale**:
- The nmcli-based roles are NOT currently used by any hosts
- No backward compatibility concerns exist
- Clean replacement avoids role proliferation and confusion
- Follows repository pattern of clear, single-purpose roles

### 2. Primary Network Device Definition
**Decision**: Create new `host_primary_interface` variable

**Rationale**:
- Cleaner separation: network configuration uses dedicated variables
- More explicit: subnet is configurable per-host instead of defaulted
- Avoid variable name confusion between DNS registration and network config
- `configure_dns_linkdevice_physical` can remain for DNS-specific purposes

### 3. DHCP vs Static Decision Logic
**Decision**: Use presence/absence of `host_ipv4` variable

**Rationale**:
- Current pattern: Hosts with static IPs define `host_ipv4: 192.168.1.x`
- Current pattern: Hosts on DHCP have `host_ipv4:` (empty) or omit it
- This is already the implicit convention (dns and host-albion have empty values)
- Simple, declarative approach that matches existing practice

**Implementation**:
```yaml
# Static IP hosts
host_ipv4: 192.168.1.116

# DHCP hosts
host_ipv4:  # Empty for DHCP
```

### 4. Renderer Choice
**Decision**: Use networkd renderer

**Rationale**:
- virtual-hetzner already uses networkd successfully
- Ubuntu Server default (lightweight, systemd-integrated)
- No desktop/GUI requirements for server infrastructure
- Consistent with existing netplan implementation

### 5. Default Values Strategy
**Decision**: Provide comprehensive defaults with minimal required overrides

**Rationale**:
- Gateway: Default to 192.168.1.1 (current pattern in network-ip-address-static)
- Netmask: Default to /24 (matches all current host_ipv4 definitions)
- Interface: Default to eth0 (fallback for Raspberry Pis)
- DNS: No defaults (let systemd-resolved handle it, or hosts can override)

### 6. Bootstrap Integration
**Decision**: Add netplan.io to bootstrap-ubuntu-server packages

**Rationale**:
- Netplan is fundamental infrastructure, should be present early
- Follows pattern of other core packages (iptables, util-linux-extra)
- Ensures availability before network configuration roles run

### 7. Role Structure
**Decision**: Create unified `network-netplan` role

**Rationale**:
- Single role handles both DHCP and static configurations via template logic
- Simpler than maintaining separate roles
- Matches virtual-hetzner pattern of conditional template rendering
- Easier to maintain and test

### 8. Cloud-Init Handling
**Decision**: Disable cloud-init network management

**Rationale**:
- Cloud-init's default netplan config enables DHCP
- Without disabling, both configs merge causing dual IPs
- Creates override at `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg`
- Removes `/etc/netplan/50-cloud-init.yaml`

## Implementation Steps

### Phase 1: Create New Netplan Role

**1.1: Create role structure**
```
ansible/roles/network-netplan/
├── defaults/main.yaml
├── tasks/main.yaml
├── handlers/main.yaml
├── templates/50-primary-interface.yaml.j2
└── README.md
```

**1.2: Define defaults**
```yaml
network_netplan_interface: "{{ host_primary_interface | default('eth0') }}"
network_netplan_gateway: "192.168.1.1"
network_netplan_subnet: "{{ host_ipv4_subnet | default(24) }}"
network_netplan_nameservers: []
network_netplan_renderer: networkd
network_netplan_mode: "{{ 'static' if (host_ipv4 | default('', true)) else 'dhcp' }}"
```

**1.3: Create tasks**
- Install netplan.io package
- Disable cloud-init network configuration
- Remove cloud-init netplan file
- Deploy primary interface netplan configuration
- Stop/disable NetworkManager if present

**1.4: Create handler**
- Apply netplan with `netplan apply`

**1.5: Create template**
- Single flexible template with conditional blocks for DHCP/static

### Phase 2: Update Bootstrap Role

**2.1: Add netplan.io to bootstrap packages**

Modify `ansible/roles/bootstrap-ubuntu-server/defaults/main.yaml`:
- Add `netplan.io` to package list

### Phase 3: Update Host Playbooks

**3.1: Add network-netplan role to all bare-metal playbooks**

Update each host playbook to include the new role early in the bootstrap process, after bootstrap-ubuntu-server, before other services.

**Hosts to update (7 Ubuntu hosts)**:
1. belinda
2. dns
3. host-albion
4. host-backups
5. host-homeassistant
6. host-storage
7. router

**Excluded**: pikvm (runs Arch Linux/PiKVM OS)

### Phase 4: Add Host Variables

**4.1: Add network variables to all host_vars**

**New required variables for all hosts**:
- `host_primary_interface`: Primary network interface name

**New required variables for static IP hosts**:
- `host_ipv4_subnet`: Subnet prefix (e.g., 24 for /24)

**Static IP hosts (6)**:
- host-storage: enp3s0, 192.168.1.116/24
- belinda: eth0, 192.168.1.150/24
- host-homeassistant: enp1s0, 192.168.1.130/24
- host-backups: enp3s0, 192.168.1.118/24
- router: eth0, 192.168.1.221/24

**DHCP hosts (2)**:
- dns: eth0
- host-albion: eth0

### Phase 5: Remove Old Roles

**5.1: Delete unused nmcli-based roles**
- `ansible/roles/network-ip-address-static/`
- `ansible/roles/network-ip-address-dhcp/`

**Keep**: `network-ip-address-forwarding` (uses sysctl, actively used by host-albion)

### Phase 6: Testing Strategy

**6.1: Pre-deployment validation**
1. Syntax check: `ansible-playbook <playbook> --syntax-check`
2. Dry run: `ansible-playbook <playbook> --check --diff`
3. Template validation: Manually render template with test data

**6.2: Phased rollout**

**Phase A: Test on belinda (non-critical Raspberry Pi)**
- Validates Raspberry Pi compatibility
- Tests static IP configuration
- Less critical than production servers

**Phase B: Test on dns (DHCP test)**
- Validates DHCP mode logic
- Tests different hardware

**Phase C: Production rollout**
1. host-storage
2. host-homeassistant
3. host-backups
4. host-albion
5. router

**6.3: Validation checks per host**

After deployment:
```bash
# Check netplan config exists
ansible [host] -m shell -a "cat /etc/netplan/50-primary-interface.yaml"

# Validate netplan syntax
ansible [host] -m shell -a "netplan generate"

# Check active network
ansible [host] -m shell -a "ip addr show"
ansible [host] -m shell -a "ip route show"

# Verify connectivity
ansible [host] -m ping
```

**6.4: Rollback procedure**

If networking fails:
1. Access via Tailscale/physical console/PiKVM
2. Remove netplan config: `rm /etc/netplan/50-primary-interface.yaml`
3. Manually configure network with `ip` commands temporarily
4. Investigate and fix template/variables

### Phase 7: Documentation Updates

**7.1: Update CLAUDE.md**

Add network-netplan role to network-* section with description

**7.2: Create role README**

Document variables, examples, and usage patterns

## Risk Mitigation

### High-Risk Items

**Network connectivity loss**:
- ✅ Tailscale provides out-of-band access
- ✅ Physical access available for Raspberry Pis
- ✅ PiKVM available for rack-mounted servers

**Incorrect interface detection**:
- ✅ All hosts will have `host_primary_interface` explicitly defined
- ✅ Dry-run mode validates before apply

**Gateway misconfiguration**:
- ✅ Default gateway (192.168.1.1) matches current network
- ✅ Can be overridden per-host if needed

### Medium-Risk Items

**NetworkManager conflicts**:
- ✅ Tasks explicitly stop/disable NetworkManager
- ✅ Netplan takes precedence

**Netplan package availability**:
- ✅ Bootstrap role installs early
- ✅ virtual-hetzner proves package availability

## Expected Outcomes

### Files Created (5)
1. `ansible/roles/network-netplan/defaults/main.yaml`
2. `ansible/roles/network-netplan/tasks/main.yaml`
3. `ansible/roles/network-netplan/handlers/main.yaml`
4. `ansible/roles/network-netplan/templates/50-primary-interface.yaml.j2`
5. `ansible/roles/network-netplan/README.md`

### Files Modified (16)
**Roles (1)**:
- `ansible/roles/bootstrap-ubuntu-server/defaults/main.yaml`

**Playbooks (7)**:
- All bare-metal Ubuntu host playbooks

**Host Variables (7)**:
- All Ubuntu host_vars files

**Documentation (1)**:
- `CLAUDE.md`

### Files Deleted (2 directories)
1. `ansible/roles/network-ip-address-static/`
2. `ansible/roles/network-ip-address-dhcp/`

## Implementation Status

### ✅ Completed

- [x] Created network-netplan role with all files
- [x] Added netplan.io to bootstrap-ubuntu-server
- [x] Updated all 7 Ubuntu host_vars files
- [x] Updated all 7 bare-metal playbooks
- [x] Tested on belinda (static IP) - PASS
- [x] Tested on dns (DHCP) - PASS
- [x] Fixed cloud-init conflict bug
- [x] Fixed mode detection bug for empty YAML values
- [x] Removed old nmcli roles
- [x] Updated CLAUDE.md documentation
- [x] Committed changes (commit 1bb0093)

### ⏳ Pending

- [ ] Deploy to host-storage
- [ ] Deploy to host-homeassistant
- [ ] Deploy to host-backups
- [ ] Deploy to host-albion
- [ ] Deploy to router
- [ ] Verify router interface name (assumed eth0)

## Bugs Fixed During Implementation

### Bug 1: Cloud-Init DHCP Conflict

**Problem**: Belinda had both static IP (192.168.1.150) and DHCP IP (192.168.1.225)

**Root Cause**: Cloud-init's netplan configuration (50-cloud-init.yaml) was still active and enabling DHCP

**Solution**:
- Create `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` with `network: {config: disabled}`
- Remove `/etc/netplan/50-cloud-init.yaml`

**Location**: `ansible/roles/network-netplan/tasks/main.yaml`

### Bug 2: Empty host_ipv4 Triggering Static Mode

**Problem**: DNS host generated malformed config with `- /24` as address

**Root Cause**: YAML empty value (`host_ipv4:`) becomes `None` in Jinja2, not empty string. The check `host_ipv4 != ''` doesn't catch `None`

**Solution**: Changed mode detection to `host_ipv4 | default('', true)` which uses truthiness test

**Location**: `ansible/roles/network-netplan/defaults/main.yaml:20`

## Notes for Future Reference

### Configuration Examples

**Static IP** (belinda):
```yaml
host_primary_interface: "eth0"
host_ipv4: 192.168.1.150
host_ipv4_subnet: 24
```

**DHCP** (dns):
```yaml
host_primary_interface: "eth0"
# host_ipv4 left empty or undefined
```

### Known Limitations

1. **Single interface only**: Role configures only primary interface
2. **IPv4 only**: No IPv6 support currently
3. **No VLAN support**: Template doesn't handle VLANs
4. **No bonding/bridging**: Can be added if needed

### Critical Dependencies

- Bootstrap role must run before network-netplan (provides netplan.io)
- Network-netplan should run before services needing network (compositions, NFS, etc.)
