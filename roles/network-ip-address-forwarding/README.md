# Network IP Address Forwarding

This role enables IPv4 forwarding on the host and makes it persist, through sysctl.

Hosts that route packets between network interfaces need this setting. Examples include Tailscale exit nodes, container networking bridges, VPN gateways, and any service that acts as a router. The `ansible.posix.sysctl` module writes the setting persistently, so it survives reboots.

## Design Notes

- The role always enables `net.ipv4.ip_forward = 1`. It has no variables.
- The task file includes IPv6 forwarding (`net.ipv6.ip_forward`), but comments it out.
- This role is deliberately narrow: single-purpose, with no configuration surface.
