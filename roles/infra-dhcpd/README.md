# Infrastructure DHCP Server

Installs and configures ISC DHCP server (`isc-dhcp-server`) on an Ubuntu host, providing dynamic address assignment for a subnet with static leases for known unmanaged devices.

The role is designed for a home network where most infrastructure hosts have static IPs managed by Ansible, but IoT devices, printers, and other unmanaged equipment need DHCP. Static leases for unmanaged devices are derived directly from the Ansible inventory — any host in the `unmanaged` group with `host_mac` and `host_ipv4` variables defined will receive a fixed DHCP lease.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `dhcpd_enabled` | `false` | Start and enable the service. Disabled by default as a safety guard. |
| `dhcpd_interface` | `eth0` | Interface the DHCP server listens on |
| `dhcpd_subnet` | `192.168.1.0` | Subnet address |
| `dhcpd_subnet_mask` | `255.255.255.0` | Subnet mask |
| `dhcpd_routers` | `192.168.1.1` | Default gateway advertised to clients |
| `dhcpd_dns_servers` | `["192.168.1.2"]` | DNS servers advertised to clients |
| `dhcpd_domain_name` | `{{ domainname_infra }}` | Domain name suffix advertised to clients |
| `dhcpd_default_lease_time` | `86400` | Default lease time in seconds (24h) |
| `dhcpd_max_lease_time` | `86400` | Maximum lease time in seconds (24h) |
| `dhcpd_range_start` | `192.168.1.100` | Start of dynamic address pool |
| `dhcpd_range_end` | `192.168.1.199` | End of dynamic address pool |
| `dhcpd_unmanaged_group` | `unmanaged` | Ansible inventory group whose members get static leases |

## Static Leases

Any host in the `dhcpd_unmanaged_group` inventory group with the following `host_vars` set will receive a static DHCP lease:

- `host_mac` — MAC address of the device
- `host_ipv4` — Fixed IP address to assign
- `host_name` — Hostname advertised via DHCP option

## Design Notes

- `dhcpd_enabled: false` is intentional — accidentally starting a rogue DHCP server on a network causes serious disruption. The service must be explicitly enabled per-host.
- The template uses `lstrip_blocks` to keep Jinja2 loop whitespace clean in the generated config file.
- Configuration changes and interface changes both notify the `Restart dhcpd` handler.
