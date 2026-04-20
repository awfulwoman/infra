# Network IP Address Forwarding

Enables and persists IPv4 forwarding on the host via sysctl.

This is required for hosts that need to route packets between network interfaces — Tailscale exit nodes, container networking bridges, VPN gateways, or any service acting as a router. The `ansible.posix.sysctl` module writes the setting persistently so it survives reboots.

## Design Notes

- No variables. The role unconditionally enables `net.ipv4.ip_forward = 1`.
- IPv6 forwarding (`net.ipv6.ip_forward`) is present in the task file but commented out.
- Intentionally a narrow, single-purpose role with no configuration surface.
