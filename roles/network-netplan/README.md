# network-netplan

Configures network interfaces using netplan.

## Mode Detection (primary interface)

- **Static IP:** When `host_ipv4` is defined and non-empty
- **DHCP:** When `host_ipv4` is undefined or empty

## Design Notes

### Why `host_ipv4` is not inside `network_netplan_config`

`host_ipv4` is a host-identity variable, not a networking configuration variable.
It is used by other roles (e.g. `infra-named` for DNS A/PTR records) that iterate
`hostvars` across all hosts. Burying it inside a role-specific dict would break
those consumers and make inventory harder to read.

The role auto-derives the primary interface config from `host_ipv4`,
`host_primary_interface`, and `host_ipv4_subnet` at runtime via `set_fact`.

### How the config is built

A `set_fact` task constructs a netplan-native dict from the flat host vars,
then deep-merges `network_netplan_config` (from host_vars) over the top via
`combine(recursive=true)`. The template just dumps the result — no logic.

This approach is necessary because Ansible YAML files cannot use variable
expressions as dict keys, so the interface-name-keyed structure netplan requires
must be assembled at task execution time.

## Additional IP addresses

Set `host_ipv4_extra` in `host_vars` to assign additional static CIDRs to the primary interface alongside DHCP or the primary static IP. Works in both modes.

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

Note: because `combine(recursive=true)` replaces lists and dicts at the key
level, defining `ethernets` in `network_netplan_config` fully replaces the
auto-generated single-interface entry. Multi-NIC hosts own their complete
interface definition.
