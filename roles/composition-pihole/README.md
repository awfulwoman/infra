# Pi-hole

[Pi-hole](https://pi-hole.net) is a network-level ad and tracker blocker acting as a DNS sinkhole. It intercepts DNS queries on the local network and blocks requests to known ad/tracker domains, providing a cleaner browsing experience for all connected devices without requiring per-device configuration.

The role disables Ubuntu's `systemd-resolved` DNS stub listener on port 53 and symlinks `/etc/resolv.conf` to avoid conflicts with Pi-hole binding to that port.

Pi-hole is not routed through Traefik (labels are commented out) — the web admin UI is served directly on port `80`.

## Ports

| Port | Purpose |
|------|---------|
| `53/tcp` and `53/udp` | DNS |
| `80/tcp` | Admin web UI |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/etc-pihole` | Pi-hole configuration and blocklists |
| `{{ composition_config }}/etc-dnsmasq.d` | dnsmasq configuration (DHCP leases, CNAMEs, custom A records) |

## Notes

- DHCP server is not enabled (port 67 is commented out).
- Templates for static DHCP leases (`04-pihole-static-dhcp.conf`), CNAMEs (`05-cnames.conf`), custom A records (`custom.list`), and work domain filtering (`07-work.conf`) exist in the role but are commented out in the task file — enable as needed.
