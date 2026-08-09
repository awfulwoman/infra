# Router (bertha)

`router-4gb-bertha` is the home network's router and gateway. It is a
dual-NIC Linux host between the LAN and the upstream Fritz!Box. It does NAT,
DHCP, and authoritative DNS for the internal network. It replaced `deedee`
as the primary DHCP and DNS server.

Bertha's configuration lives in
`inventory/host_vars/router-4gb-bertha/core.yaml`.
`playbooks/hosts/router-4gb-bertha/core.yaml` applies it.

This document covers bertha itself. For the network around it — the
tailnet, the address plan, and the three DNS resolution paths — read
[networking.md](networking.md).

## NIC layout

Bertha has two physical NICs, and their roles must be correct. If you swap
them, or name a third NIC that does not exist, all outbound traffic
black-holes.

| NIC      | Role | Address               | Notes |
|----------|------|-----------------------|-------|
| `enp2s0` | WAN  | DHCP from Fritz!Box   | Upstream gateway `192.168.178.1`; supplies the default route |
| `enp1s0` | LAN  | `192.168.1.1/24` (static) | Bertha is the gateway for the `192.168.1.0/24` home network |

The `wan_iface` and `lan_iface` host_vars must always match the netplan
`ethernets:` keys above. `network-routing-basic` runs an assert task that
checks both are set and distinct before it changes any rules.

## The role stack

Roles run in this order (each builds on the previous):

- `bootstrap-ubuntu-server`: base host setup. It needs a working WAN first.
- `network-netplan`: renders netplan. The WAN is the netplan **primary**, in
  `dhcp` mode — see the default-route trap below for why. It keeps the LAN's
  static `192.168.1.1`.
- `network-routing-basic`: IPv4 forwarding, NAT, and the firewall.
- `infra-dhcpd`: the LAN's DHCP server.
- `infra-named`: the LAN's authoritative DNS server, and its ad blocker.

## NAT and forwarding

`network-routing-basic` enables `net.ipv4.ip_forward` and MASQUERADEs
outbound traffic on the WAN (`enp2s0`), so the `192.168.1.0/24` LAN reaches
the internet through a single upstream address. FORWARD rules permit
LAN→WAN and established/related return traffic.

`iptables-persistent` makes iptables rules reboot-safe: every
rule-modifying task notifies a single `Save iptables rules` handler, which
runs `netfilter-persistent save`.

## Firewall

The `network_routing_firewall: true` setting turns hardening on. When it is
enabled, INPUT and FORWARD default to **DROP**, with an allow-list for:

- loopback and established/related traffic,
- Tailscale (`tailscale0`) — the out-of-band management backstop,
- specific TCP/UDP service ports **from the LAN only**
  (`network_routing_input_tcp_ports` / `network_routing_input_udp_ports`),
- ICMP from the LAN.

The WAN cannot reach the router or start forwards. Tailscale is a separate
tunnel, so tightening the firewall cannot lock you out of management.

## DHCP

`infra-dhcpd` runs the ISC DHCP server. It binds to the LAN NIC only
(`dhcpd_interface: enp1s0`). It hands out **only** bertha (`192.168.1.1`) as
the resolver. This is deliberate: it is not a public secondary, so clients
cannot fall through and bypass bertha's split-horizon DNS.

> The role default binds to `enp3s0`, a NIC bertha does not have. At the
> default, the server serves nobody. The `dhcpd_interface` override is
> mandatory here.

Static leases for unmanaged IoT devices come from the `unmanaged` inventory
group (`host_ipv4`/`host_mac` in `inventory/hosts-unmanaged.yaml`). See
`roles/infra-dhcpd/README.md` for details. If a device with a static lease
looks unreachable, check the WiFi layer before the DHCP layer. See
[wifi.md](wifi.md) for a case where the DHCP config was not at fault, but
the device did not connect.

## DNS

`infra-named` (BIND9) is authoritative for the internal domain. It does
split-horizon resolution with two views, selected on the source address of
the query: a LAN client (`192.168.1.0/24`) gets the LAN address of a host,
and a tailnet client (`100.64.0.0/10`) gets its Tailscale address. Bertha
advertises itself as the sole nameserver (`dns01 → 192.168.1.1`). See
[networking.md](networking.md) for the full resolution paths.

BIND is deliberately kept off the WAN. `bind_listen_on` binds everywhere
*except* the WAN subnet (`!192.168.178.0/24; any;`), and `bind_listen_on_v6`
is `none;`. The firewall already blocks WAN:53. This removes the listener
too, as defence in depth.

Legacy devices still searching the previous internal domain
(`i.affordablepotatoes.com`) resolve through a **DNAME alias** to the
current domain (`bind_dname_aliases`). For example,
`jellyfin.i.affordablepotatoes.com` resolves to the current `jellyfin.*`
record. The devices need no change.

## Ad blocking

Because `infra-dhcpd` hands out bertha as the *only* resolver, a client
cannot bypass ad blocking by choice of a different DNS server. Blocking
uses BIND **Response Policy Zones**, not a Pi-hole. RPZ uses the same "lie
about ad domains" mechanism, but it runs inside the BIND resolver that
already runs on bertha. This keeps the router's no-Docker footprint, and
leaves the inventory-generated zones above untouched.

`bind_rpz_enabled: true` pulls HaGeZi Multi Normal (~181k domains) as a
policy zone. A daily systemd timer (`bind-rpz-refresh.timer`) re-fetches
it, validates it with `named-checkzone`, and `rndc reload`s just that zone.
It never installs a list that fails validation. It never restarts named,
because a restart throws away the resolver cache. Loading the list costs
named about 250 MB of RSS.

A local `rpz.allowlist` policy zone is listed **first**, so an
`rpz-passthru` entry there beats every blocklist. It always contains the
internal domain and the DNAME aliases, so no public blocklist can shadow
our own names.

**Runbook — a site is broken and you suspect blocking:**

```bash
# The RPZ log names the exact rule that fired
grep <domain> /var/log/named/rpz.log
```

Add the domain to `bind_rpz_allowlist_extra` in bertha's host_vars. Then
re-run the role. See `roles/infra-named/README.md` for the blocklist
tiers.

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

- **WAN (`enp2s0`)** — without `accept-ra: false` and `dhcp6: false`, the
  interface silently SLAAC-autoconfigures a *public, globally-routable*
  IPv6 address from the Fritz!Box's router advertisements. There is no
  `ip6tables` ruleset, so that address is completely unfiltered. The
  setting keeps bertha's WAN attack surface to the firewalled IPv4 side
  only. Link-local (`fe80::`) remains. This is harmless: it is not
  routable off-link.
- **LAN (`enp1s0`)** — a router must never learn routing from its own
  clients. A live check found another LAN device that sent router
  advertisements. This interface accepted them by default. `accept-ra:
  false` refuses them now.

A full dual-stack build was scoped, and deliberately deferred. It needs
three things: DHCPv6-PD on the WAN through `dhcpcd`, RA/SLAAC to the LAN
through `radvd`, and an `ip6tables` mirror of the v4 firewall. IPv6 has no
NAT, so every LAN device becomes directly internet-addressable without a
v6 firewall. This makes the v6 firewall load-bearing, not optional.
Bertha uses the smaller "suppress the unprotected WAN address" change
above instead.

## Design traps worth remembering

**Netplan static-mode default-route trap.** In `static` mode, the
`network-netplan` role emits `default via {{ network_netplan_gateway }}`.
On a router whose "gateway" default equals its own LAN IP
(`192.168.1.1`), that is a default route that points at *itself*. This
black-holes all outbound traffic. Bertha sidesteps this by making the WAN
the **DHCP primary**, so the upstream Fritz!Box (`192.168.178.1`) supplies
the real default route.

**Stale installer netplan file.** netplan merges *every* file in
`/etc/netplan`. A leftover `00-installer-config.yaml`, written by the
Ubuntu installer, silently combines with the role's authoritative
`50-primary-interface.yaml`. On bertha, the installer file carried the
exact self-referential `default via 192.168.1.1` route above. It lay
dormant until a `netplan apply` re-merged it, and black-holed the WAN. The
`network-netplan` role now removes `00-installer-config.yaml` on every
run, so it cannot resurface.

Corollary: any `netplan apply` on a router re-evaluates all files. It has
the same blast radius as a routing change. **Treat even a one-line IPv6
edit as a routing change, and stage it behind a rollback safety net.**

**Duplicate-CNAME zone failure.** `infra-named` aggregates `cnames` from
every host in the `infra` group into one forward zone. A CNAME is a
singleton RR type. If the same name is declared on two hosts, named
rejects the *entire* zone, and all DNS goes down. The role guards against
this with a pre-render assertion that fails early. The assertion lists
the offending duplicates.

## Relevant roles

- `network-netplan`: netplan rendering (see `roles/network-netplan/README.md`).
- `network-routing-basic`: forwarding, NAT, and firewall.
- `infra-dhcpd`: LAN DHCP server.
- `infra-named`: LAN authoritative / split-horizon DNS, plus RPZ ad blocking.
