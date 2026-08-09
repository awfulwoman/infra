# Networking

How the home network fits together, and how it meets Tailscale.

`router-4gb-bertha` is at the centre. Bertha is the gateway, the DHCP
server, and the authoritative DNS server. This document covers the network
as a whole. For bertha's own internals — NAT, the firewall, RPZ ad
blocking, the IPv6 stance — read [router.md](router.md).

## Two networks

The infrastructure runs on two IP networks at the same time.

| Network | Range | Gateway | Who is on it |
|---------|-------|---------|--------------|
| LAN | `192.168.1.0/24` | bertha (`192.168.1.1`) | Every device in the home, managed and unmanaged |
| Tailnet | `100.80.0.0/16` | none (mesh) | Every managed host, plus the user's phone and laptop |

Upstream of the LAN is a Fritz!Box on `192.168.178.0/24`. Bertha's WAN NIC
takes a DHCP address there. The Fritz!Box supplies the default route.

```text
                     internet
                        |
                 Fritz!Box 192.168.178.1
                        |  (WAN, enp2s0, DHCP)
                     BERTHA
        192.168.1.1 (LAN, enp1s0)   100.80.1.1 (tailscale0)
                        |                    :
        ----------------+------------        :  tailnet mesh
        |               |          |         :  (no route to the LAN)
   storage .116    malcolm .99   IoT ...     :
   100.80.1.116   100.80.1.99                :
        :               :                    :
        ....... each host joins the tailnet itself ......
```

## The address plan

A host keeps the same last octets on both networks. A host on
`192.168.1.X` takes `100.80.1.X`. This makes an address on one network
readable as an address on the other.

| Host | LAN | Tailnet |
|------|-----|---------|
| bertha | `192.168.1.1` | `100.80.1.1` |
| storage | `192.168.1.116` | `100.80.1.116` |
| malcolm | `192.168.1.99` | `100.80.1.99` |

Hosts with no LAN presence get addresses from `100.80.2.0/24` in sequence.
There are two at present: `vps-hetzner-public01` (`100.80.2.1`) and
`raspberry-pi4-4gb-albion` (`100.80.2.2`).

Each host declares its address as `host_tailscale_ipv4` in its `host_vars`.
The address is inventory data, not something Tailscale chooses. The
[`network-tailscale-address`](../roles/network-tailscale-address/README.md)
role holds the device to it through the Tailscale API.

## The two networks do not route into each other

This is the most important fact in this document, because most of the DNS
design follows from it.

No host advertises a subnet route. Nothing in this repository passes
`--advertise-routes`. As a result:

- A client that is only on the tailnet cannot reach `192.168.1.0/24` at
  all. A LAN address is a dead end from a phone on mobile data.
- Bertha's LAN address (`192.168.1.1`) is not reachable over the tailnet
  either. Tailnet clients must use `100.80.1.1`.
- Every managed host joins the tailnet on its own. The tailnet is a mesh of
  hosts, not a tunnel into the LAN.

One host advertises an exit node: `raspberry-pi4-4gb-albion`, through
`tailscale_exit_node: true`. An exit node carries general internet traffic.
It is not a route into the home LAN.

## Four ways to name a host

| Form | Example | Resolved by | Answer |
|------|---------|-------------|--------|
| Plain name | `server-64gb-storage.xberg.ber.<domain>` | bertha, split-horizon | Depends on where the query comes from |
| `ts.` name | `ts.server-64gb-storage.xberg.ber.<domain>` | bertha | Always the Tailscale address |
| MagicDNS | `apple-macmini-m4-16gb-malcolm.<tailnet>.ts.net` | Tailscale | Always the Tailscale address |
| Service label | `jellyfin.<domain>` | bertha or Hetzner | CNAME onto the host's plain name |

The plain name is the one that changes with the vantage of the client. Use
a `ts.` name in a configuration file when the tailnet path is the one you
want, whatever the client. Compositions do this today, so that a service on
one host reaches a service on another without a hardcoded `100.x` address.

## Name resolution: three paths

The same service name resolves through three separate paths. The path
depends on where the client is and which resolver it uses.

| Path | Client | Resolver | Answer |
|------|--------|----------|--------|
| 1 | On the LAN, not on the tailnet | bertha at `192.168.1.1`, from DHCP | LAN address (`192.168.1.x`) |
| 2 | On the tailnet — **including every managed host** | bertha at `100.80.1.1` | Tailscale address (`100.80.x.x`) |
| 3 | Anywhere, public resolver | Hetzner public zone | Tailscale address (`100.80.x.x`) |

Path 1 covers the devices that are on the LAN but **not** on the tailnet:
IoT devices, the TV, guests. `infra-dhcpd` hands out bertha as the **only**
resolver. Such a client therefore cannot fall through to a public resolver
and bypass the internal zone or the ad blocking.

Path 2 covers a phone on mobile data — and also **every managed host**,
including the ones sitting on the LAN. This surprises people, so it is
worth stating plainly:

> A managed host does not use path 1. Tailscale claims the `~.` routing
> domain on each enrolled host, so all of its DNS goes to `100.100.100.100`
> and on to the tailnet's global nameserver, which is bertha. The query
> arrives at bertha from the host's `100.x` address and matches the
> `Tailscale` ACL.

Confirm it on any managed host:

```bash
resolvectl domain | grep -A1 tailscale0    # shows "~."
getent ahostsv4 <this host's own FQDN>     # returns 100.80.x.x, not 192.168.1.x
```

Two consequences follow. Managed hosts reach each other over the tailnet,
never over the LAN, even when a LAN cable joins them. And a wrong
`host_tailscale_ipv4` breaks host-to-host traffic, because the name every
composition uses resolves through this view.

The tailnet's global nameserver is set to `100.80.1.1`. That setting lives
in the Tailscale admin console, not in this repository. It is readable
through the API:

```bash
GET /api/v2/tailnet/-/dns/nameservers   →   {"dns": ["100.80.1.1"]}
```

Path 3 is the fallback for a client that does not use bertha as its
resolver. The public zone is deliberately populated with **Tailscale**
addresses, not LAN addresses. See `plugins/filters/dns_records.py`, where
each host's public A record targets `tailscale_ipv4`. A public answer is
therefore useless to an attacker and correct for the user, because only a
tailnet member can route to `100.80.x.x`.

Two vantages matter enough that the repository captures both. The snapshot
harness records how every service name resolves from the LAN and from
`public01`. See [snapshots/README.md](snapshots/README.md).

## How bertha chooses the answer

`bind_split_horizon_enabled: true` in bertha's `host_vars` turns on two
BIND views. Bertha is the only host where this setting is meaningful,
because it is the only DHCP-advertised resolver.

The views select on the **source address** of the query, not on the
interface:

```text
view "lan"        match-clients { localhost; LAN; }        192.168.1.0/24
view "tailscale"  match-clients { Tailscale; }             100.64.0.0/10
```

The ACL groups come from `bind_acl_groups` in `roles/infra-named/defaults/main.yaml`.
The `Tailscale` ACL covers the whole CGNAT range `100.64.0.0/10`, not only
the `100.80.0.0/16` block in use here.

Each view gets its own zone file, rendered from the same template with a
different address field:

| View | Zone file | `bind_zone_ip_field` |
|------|-----------|----------------------|
| `lan` | `db.<domain>.lan.zone` | `host_ipv4` |
| `tailscale` | `db.<domain>.tailscale.zone` | `host_tailscale_ipv4` |

Three consequences follow:

- **Ad blocking applies to both views.** BIND requires that an RPZ zone
  named in a view's `response-policy` is a real zone inside that same
  view. `in-view` does not satisfy this. The RPZ zone declarations are
  therefore duplicated per view on purpose.
- **DNAME aliases are shared.** Alias zones carry no host-specific
  address, so the `tailscale` view pulls them with `in-view "lan"`.
- **The `tailscale` view serves no reverse zone.** A PTR query through
  that view returns REFUSED. Tailscale addresses reverse under
  `100.in-addr.arpa`, which bertha does not serve, and MagicDNS already
  covers it.

Bertha listens on the tailnet address as well as the LAN one.
`bind_listen_on` is `!192.168.178.0/24; any;`, which excludes only the WAN
subnet.

## Tailscale is the management backstop

Bertha's firewall defaults both INPUT and FORWARD to DROP. One rule accepts
everything that arrives on `tailscale0`:

```yaml
- name: Allow INPUT from Tailscale (out-of-band management backstop)
  ansible.builtin.iptables:
    chain: INPUT
    in_interface: tailscale0
    jump: ACCEPT
```

The tailnet is a separate path from the LAN and the WAN. A wrong LAN rule,
a wrong NIC name, or a broken netplan file therefore cannot remove all
management access.

CAUTION: The backstop works only while `tailscaled` runs. A reboot into a
broken network configuration, or a change that stops the Tailscale service,
removes it. Stage routing changes and netplan changes behind a rollback
safety net. Read the design traps in [router.md](router.md) first.

## How a host joins the tailnet

`bootstrap-ubuntu-server` enrols every managed Ubuntu host. The steps run
in this order:

1. Read `tailscale status --json`. If the host is already connected, skip
   enrolment.
2. Mint a one-time auth key with
   [`network-tailscale-authkey`](../roles/network-tailscale-authkey/README.md).
   The key is pre-authorised, not reusable, tagged `tag:auto-generated`,
   and expires after 300 seconds.
3. Run `artis3n.tailscale.machine` to bring the node up. If
   `tailscale_exit_node` is true, add `--advertise-exit-node`.
4. Pin the inventory address with `network-tailscale-address`.

All three roles get their API credentials through
[`network-tailscale-token`](../roles/network-tailscale-token/README.md),
which exchanges an OAuth client for a bearer token once per play. The
OAuth client needs two scopes: `auth_keys` for enrolment, and write access
to `devices:core` for the address pinning. A missing scope fails with
`403`.

`apple-macmini-m4-16gb-malcolm` is the exception. Its Tailscale is a
Homebrew cask installed by hand, so nothing enforces its address. The
inventory value is declarative only, and `infra-named` publishes it. If the
admin console and the inventory disagree, the DNS record points somewhere
wrong.

## Traps at the boundary

**A changed Tailscale address drops every connection to the host.** That is
Tailscale's behaviour. `ansible_host` is a LAN address for most hosts, so
Ansible survives. Hosts reached by a MagicDNS name (albion) lose the
connection mid-play and need the playbook run again. Clients also cache the
old address. Flush DNS with `scripts/flush-dns-macos.sh` or
`scripts/flush-dns-ubuntu.sh`.

**One name, two addresses, one certificate.** Bertha mints a production
wildcard certificate for the internal domain and distributes it. The same
name works on both paths, so a single certificate covers the LAN answer and
the tailnet answer. A separate name per path needs a certificate per path.

**Public DNS publication is add-only.** `bind_public_dns_enabled: true` is
set on bertha alone. The task creates and updates the names it derives from
inventory. It never deletes a name outside that set, so a legacy record
from the old self-registration mechanism stays until a current label
collides with it.

**A duplicate CNAME takes down all DNS.** `infra-named` aggregates the
`cnames` of every host in the `infra` group into one zone. A CNAME is a
singleton record type, so a name declared on two hosts makes named reject
the whole zone. The role asserts against this before it renders, and names
the duplicates.

## Related documents

- [router.md](router.md) — bertha itself: NIC layout, NAT, firewall, DHCP,
  RPZ, IPv6 stance, design traps.
- [hosts.md](hosts.md) — the fleet, and what each machine does.
- [wifi.md](wifi.md) — the wireless layer below the LAN.
- [snapshots/README.md](snapshots/README.md) — LAN and remote resolution
  baselines.
- `roles/infra-named/README.md` — zone generation, `ts.` records, RPZ
  tiers.
- `roles/network-tailscale-address/README.md` — the address plan and the
  API mechanics.
