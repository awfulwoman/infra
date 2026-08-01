# network-macos-static

Sets a static IPv4 configuration on a macOS host using `networksetup`, keyed
off the existing `host_ipv4` / `host_ipv4_extra` inventory variables.

## Why this exists

Linux hosts get a static primary interface via `network-netplan`. macOS has
no netplan equivalent, so hosts like `apple-macmini-m4-16gb-malcolm` were
only ever getting `host_ipv4` as an Ansible connection variable — nothing
actually configured the interface, and the address was just whatever the
DHCP server happened to hand out (and re-lease) for that MAC.

## Design Notes

- `network_macos_static_service` is a *network service* name (as listed by
  `networksetup -listallnetworkservices`), not a device name like `en0` —
  macOS keys interface config off the service, not the BSD device.
- `networksetup -setmanual`/`-setdnsservers` are always "changed" from
  Ansible's point of view, so idempotency is done by hand: read the current
  config first, and only run the mutating command if it doesn't already
  match.
- Switching a host from DHCP to manual with the *same* IP it already holds
  (the common case here) does not interrupt connectivity — the interface
  keeps the same address, only the source of truth changes.
- DNS is set explicitly because macOS does not fall back to DHCP-provided
  DNS servers once IPv4 is set to Manual — leaving DNS unset after this role
  runs would break resolution.
