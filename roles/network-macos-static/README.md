# network-macos-static

This role sets a static IPv4 configuration on a macOS host, using
`networksetup`. It keys this off the existing `host_ipv4` and
`host_ipv4_extra` inventory variables.

## Why this exists

Linux hosts get a static primary interface through `network-netplan`. macOS
has no netplan equivalent. Because of this, hosts like
`apple-macmini-m4-16gb-malcolm` only ever got `host_ipv4` as an Ansible
connection variable. Nothing configured the interface itself, so the address
was whatever the DHCP server assigned, and re-assigned, for that MAC address.

## Design Notes

- `network_macos_static_service` is a *network service* name, as listed by
  `networksetup -listallnetworkservices`, not a device name like `en0`.
  macOS keys interface configuration off the service, not the BSD device.
- From Ansible's point of view, `networksetup -setmanual` and
  `-setdnsservers` always report a change. So the role checks idempotency by
  hand: it reads the current configuration first, and runs the mutating
  command only if that configuration does not already match.
- Switching a host from DHCP to manual, with the *same* IP it already holds,
  does not interrupt connectivity. This is the common case here: the
  interface keeps the same address, and only the source of truth changes.
- The role sets DNS explicitly. Once IPv4 is set to Manual, macOS does not
  fall back to DHCP-provided DNS servers. If DNS is left unset after this
  role runs, name resolution breaks.
