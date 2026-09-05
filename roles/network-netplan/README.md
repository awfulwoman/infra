# network-netplan

Configures network interfaces using netplan.

## Mode Detection (primary interface)

- **Static IP:** When `host_ipv4` is defined and non-empty
- **DHCP:** When `host_ipv4` is undefined or empty

## Design Notes

### Why `host_ipv4` is not inside `network_netplan_config`

`host_ipv4` is a host-identity variable, not a networking configuration
variable. Other roles use it too, for example `infra-named` for DNS A and
PTR records, and these roles iterate `hostvars` across all hosts. If this
variable were buried inside a role-specific dict, it would break those
consumers and make the inventory harder to read.

The role derives the primary interface configuration automatically from
`host_ipv4`, `host_primary_interface`, and `host_ipv4_subnet`, at runtime,
through `set_fact`.

### How the config is built

A `set_fact` task builds a netplan-native dict from the flat host variables.
It then deep-merges `network_netplan_config` (from host_vars) over the top,
through `combine(recursive=true)`. The template only writes out the result;
it contains no logic.

This approach is necessary because Ansible YAML files cannot use variable
expressions as dict keys. As a result, the role must assemble the
interface-name-keyed structure that netplan requires at task execution time.

## Additional IP addresses

Set `host_ipv4_extra` in `host_vars` to assign extra static CIDRs to the primary interface, alongside DHCP or the primary static IP. This works in both modes.

```yaml
# Hetzner Cloud: DHCP primary + routed additional IP
network_netplan_mode: dhcp
host_ipv4_extra:
  - 78.47.163.140/32
```

## Multi-interface / custom config

Set `network_netplan_config` in `host_vars` using netplan-native format.
This is deep-merged over the auto-generated primary interface config.

```yaml
# Single-NIC override (e.g. custom gateway)
network_netplan_config:
  ethernets:
    eth0:
      routes:
        - to: default
          via: 10.0.0.1

# Multi-NIC (replaces auto-generated ethernets entirely)
network_netplan_config:
  ethernets:
    eth0:          # WAN
      dhcp4: true
    eth1:          # LAN
      addresses: [192.168.1.1/24]
      nameservers:
        addresses: [1.1.1.1]
```

Note: `combine(recursive=true)` replaces lists and dicts at the key level.
Because of this, defining `ethernets` in `network_netplan_config` fully
replaces the auto-generated single-interface entry. Multi-NIC hosts own
their complete interface definition.
