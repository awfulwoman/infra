# Router (bertha)

`router-4gb-bertha` is the home network's router and gateway — a dual-NIC
Linux box that sits between the LAN and the upstream Fritz!Box, doing NAT,
DHCP, and authoritative DNS for the internal network. It replaced `deedee` as
the primary DHCP/DNS server.

All of bertha's configuration lives in
`inventory/host_vars/router-4gb-bertha/core.yaml` and is applied by
`playbooks/hosts/router-4gb-bertha/core.yaml`.

## NIC layout

Bertha has two physical NICs. Getting their roles right is load-bearing —
swapping them (or misnaming a third that doesn't exist) black-holes all
outbound traffic.

| NIC      | Role | Address               | Notes |
|----------|------|-----------------------|-------|
| `enp2s0` | WAN  | DHCP from Fritz!Box   | Upstream gateway `192.168.178.1`; supplies the default route |
| `enp1s0` | LAN  | `192.168.1.1/24` (static) | Bertha is the gateway for the `192.168.1.0/24` home network |

The `wan_iface` / `lan_iface` host_vars must always match the netplan
`ethernets:` keys above — `network-routing-basic` asserts they are set and
distinct before touching any rules.

## The role stack

Roles run in this order (each builds on the previous):

- `bootstrap-ubuntu-server`: base host setup. Needs a working WAN first.
- `network-netplan`: renders netplan. The WAN is the netplan **primary** in
  `dhcp` mode — see the default-route trap below for why. Preserves the LAN's
  static `192.168.1.1`.
- `network-routing-basic`: IPv4 forwarding, NAT, and the firewall.
- `infra-dhcpd`: the LAN's DHCP server.
- `infra-named`: the LAN's authoritative DNS server.

## NAT and forwarding

`network-routing-basic` enables `net.ipv4.ip_forward` and MASQUERADEs
outbound traffic on the WAN (`enp2s0`), so the `192.168.1.0/24` LAN reaches
the internet through a single upstream address. FORWARD rules permit
LAN→WAN and established/related return traffic.

iptables rules are made reboot-safe via `iptables-persistent`: every
rule-modifying task notifies a single `Save iptables rules` handler that runs
`netfilter-persistent save`.

## Firewall

Hardening is gated on `network_routing_firewall: true`. When enabled, INPUT
and FORWARD default to **DROP**, with an allow-list for:

- loopback and established/related traffic,
- Tailscale (`tailscale0`) — the out-of-band management backstop,
- specific TCP/UDP service ports **from the LAN only**
  (`network_routing_input_tcp_ports` / `network_routing_input_udp_ports`),
- ICMP from the LAN.

The WAN cannot reach the router or initiate forwards. Because Tailscale is a
separate tunnel, tightening the firewall can't lock you out of management.

## DHCP

`infra-dhcpd` runs the ISC DHCP server, bound to the LAN NIC only
(`dhcpd_interface: enp1s0`). It hands out **only** bertha (`192.168.1.1`) as
the resolver — deliberately not a public secondary — so clients can't fall
through and bypass bertha's split-horizon DNS.

> The role default binds to `enp3s0`, a NIC bertha does not have. Leaving it
> at the default means the server serves nobody; the `dhcpd_interface`
> override is mandatory here.

## DNS

`infra-named` (BIND9) is authoritative for the internal domain and does
split-horizon resolution — the LAN gets internal answers, the outside world
gets the public view. Bertha advertises itself as the sole nameserver
(`dns01 → 192.168.1.1`).

BIND is deliberately kept off the WAN: `bind_listen_on` binds everywhere
*except* the WAN subnet (`!192.168.178.0/24; any;`), and `bind_listen_on_v6`
is `none;`. The firewall already blocks WAN:53 — this removes the listener
too, as defence in depth.

Legacy devices still searching the previous internal domain
(`i.affordablepotatoes.com`) resolve via a **DNAME alias** onto the current
domain (`bind_dname_aliases`), so e.g. `jellyfin.i.affordablepotatoes.com`
resolves to the current `jellyfin.*` record without touching those devices.

## IPv6 stance: intentionally IPv4-only

The LAN is IPv4-only by design. Bertha does **not** route IPv6 to the LAN
(no prefix delegation, no RA/SLAAC, no `ip6tables`).

Both NICs explicitly refuse IPv6 autoconfiguration in netplan:

```yaml
enp2s0: # WAN
  dhcp4: true
  dhcp6: false
  accept-ra: false
enp1s0: # LAN
  accept-ra: false
```

Why this matters:

- **WAN (`enp2s0`)** — without `accept-ra: false` / `dhcp6: false`, the
  interface silently SLAAC-autoconfigures a *public, globally-routable* IPv6
  address from the Fritz!Box's router advertisements. With no `ip6tables`
  ruleset anywhere, that address would be completely unfiltered. Suppressing
  it keeps bertha's WAN attack surface to the (firewalled) IPv4 side only.
  Link-local (`fe80::`) remains, which is harmless — it isn't routable
  off-link.
- **LAN (`enp1s0`)** — a router must never learn routing from its own
  clients. A live check found another LAN device sending router
  advertisements that this interface was willing to accept;
  `accept-ra: false` refuses them.

A full dual-stack build (DHCPv6-PD on the WAN via `dhcpcd`, RA/SLAAC to the
LAN via `radvd`, an `ip6tables` mirror of the v4 firewall) was scoped and
deliberately deferred: IPv6 has no NAT, so every LAN device would become
directly internet-addressable, making the v6 firewall load-bearing rather
than optional. The smaller "suppress the unprotected WAN address" change above
was chosen instead.

## Design traps worth remembering

**Netplan static-mode default-route trap.** In `static` mode the
`network-netplan` role emits `default via {{ network_netplan_gateway }}`. On a
router whose "gateway" default equals its own LAN IP (`192.168.1.1`), that's a
default route pointing at *itself* — which black-holes all outbound traffic.
Bertha sidesteps this by making the WAN the **DHCP primary**, so the upstream
Fritz!Box (`192.168.178.1`) supplies the real default route.

**Stale installer netplan file.** netplan merges *every* file in
`/etc/netplan`, so a leftover `00-installer-config.yaml` (written by the
Ubuntu installer) silently combines with the role's authoritative
`50-primary-interface.yaml`. On bertha the installer file carried the exact
self-referential `default via 192.168.1.1` route above; it lay dormant until a
`netplan apply` re-merged it and black-holed the WAN. The `network-netplan`
role now removes `00-installer-config.yaml` on every run so it can't resurface.
Corollary: **any `netplan apply` on a router re-evaluates all files and has the
same blast radius as a routing change — treat even a one-line IPv6 edit as a
routing change and stage it behind a rollback safety net.**

**Duplicate-CNAME zone failure.** `infra-named` aggregates `cnames` from every
host in the `infra` group into one forward zone. A CNAME is a singleton RR
type, so the same name declared on two hosts makes named reject the *entire*
zone (all DNS goes down). The role guards against this with a pre-render
assertion that fails early, listing the offending duplicates.

## Relevant roles

- `network-netplan`: netplan rendering (see `roles/network-netplan/README.md`).
- `network-routing-basic`: forwarding, NAT, and firewall.
- `infra-dhcpd`: LAN DHCP server.
- `infra-named`: LAN authoritative / split-horizon DNS.
