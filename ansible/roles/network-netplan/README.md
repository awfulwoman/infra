# network-netplan

Configures the primary network interface using netplan.

## Mode Detection

- **Static IP:** When `host_ipv4` is defined and non-empty
- **DHCP:** When `host_ipv4` is undefined or empty
