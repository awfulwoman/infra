# DNS server for home network

Based on [BIND9](https://www.isc.org/bind/) (because masochism). Ingests the Ansible inventory data and spits out [DNS zone files](https://en.wikipedia.org/wiki/Zone_file).

This role will:

* Install and configure BIND.
* Gather info about machines in the Ansible inventory.
* Assign inventory FQDNs to inventory IP addresses.
* Discover application cnames and map them to inventory FQDNs.
* Publish each host's Tailscale address under a `ts.` name.
* Generate zone files (normal and reverse).

This setup should also allow an external DHCP server to make changes via [DDNS](https://en.wikipedia.org/wiki/Dynamic_DNS).

```bash
# Check config
named-checkconf /etc/bind/named.conf.local
# Check main zone file
named-checkzone DOMAINNAME /etc/bind/zones/db.DOMAINNAME.zone
# Check reverse zone file
named-checkzone 168.192.in-addr.arpa /etc/bind/zones/db.DOMAINNAME.reverse.zone
```

## Tailscale addresses

Every host declares its Tailscale address as `host_tailscale_ipv4` in its
`host_vars` (the [`network-tailscale-address`](../network-tailscale-address/README.md)
role is what holds the device to it). This role publishes those alongside the
LAN A records, so each host ends up with a name for both paths to it:

```text
server-64gb-storage.kberg.ber                IN  A  192.168.1.116
ts.server-64gb-storage.kberg.ber             IN  A  100.80.1.116
```

That is the addressable form of "everything is accessed via Tailscale": a
composition on one host can reach a service on another over the tailnet by name,
rather than by a hardcoded `100.x` that changes the next time a device is
re-enrolled.

| Variable | Default | Purpose |
|----------|---------|---------|
| `bind_tailscale_records_enabled` | `true` | Emit the `ts.` A records at all |
| `bind_tailscale_record_prefix` | `ts` | Label prefixed to `host_pfqdn` |

Hosts without `host_tailscale_ipv4` are skipped. No PTR records are generated —
Tailscale addresses reverse under `100.in-addr.arpa`, which this role does not
serve, and MagicDNS already covers it.

## Split-horizon DNS

Off unless `bind_views_enabled: true`. Currently on for bertha only, since that
is the resolver the tailnet points at.

Every service name in this zone is a CNAME onto a host's `host_pfqdn`, and that
resolves to the host's LAN address. Fine at home; useless on a phone in a hotel,
which gets `192.168.1.116` back for `radarr.<domain>` and cannot route to it.

With views on, the same zone is rendered twice from the same template. The only
thing that differs is which inventory variable the host A records come from:

| | `radarr.<domain>` → | |
|---|---|---|
| LAN client (`192.168.1.0/24`) | `server-64gb-storage.kberg.ber` | `192.168.1.116` |
| Tailnet client (`100.64.0.0/10`) | `server-64gb-storage.kberg.ber` | `100.80.1.116` |

The CNAMEs are byte-identical between views — only the A record moves. Traefik
listens on all interfaces so it answers on either address, and the certificates
come from Let's Encrypt over DNS-01, so they validate wherever the request
lands. Nothing about the compositions changes.

| Variable | Default | Purpose |
|----------|---------|---------|
| `bind_views_enabled` | `false` | Master switch |
| `bind_views` | tailscale, internal | View name, `match-clients`, which address variable to use, and which zone file |

### This does not work on its own

Split horizon only decides *what answer* a tailnet client gets. It cannot make
the client ask bertha in the first place — that is a Tailscale admin console
setting (**DNS → Nameservers**, bertha's Tailscale address, with *Restrict to
domain* set to the infra domain if you want split DNS rather than a global
resolver). Without it the phone never reaches this zone at all.

Which is the other reason `host_tailscale_ipv4` matters: the nameserver entry
needs a Tailscale address that does not move.

### Things worth knowing

* **LAN-only devices vanish from the tailnet view.** Anything in the `unmanaged`
  group has no Tailscale address, so it is absent rather than published at an
  unreachable `192.168.x`. NXDOMAIN fails immediately; a dead LAN address hangs.
* **`ts.<host>` names are unchanged in both views** — that is how you ask for the
  tailnet path deliberately, from either side.
* **`in-view` is why view order matters.** The zones that are identical in both
  (reverse, DNAME aliases) are loaded once in the first view and referenced from
  the second, so BIND holds one copy. The declaration order is a hard
  requirement: `in-view` can only point at a view already defined.
* **BIND requires every zone to be inside a view once any view exists.** Debian's
  stock `named.conf` breaks that by including `named.conf.default-zones` at the
  top level, so enabling views makes this role take over `/etc/bind/named.conf`
  and move that include inside each view. **Turning views back off does not
  restore Debian's file** — put the include back by hand or
  `apt-get install --reinstall bind9`.
* **Ad-blocking costs twice as much with views on** — see below.

## DNS filtering (Response Policy Zones)

Optional Pi-hole-style ad/tracker blocking, done natively in BIND rather than by
bolting a second resolver onto the network. Off unless `bind_rpz_enabled: true`;
when off, the rendered config is byte-identical to a build without this feature.

[HaGeZi](https://github.com/hagezi/dns-blocklists) publishes its blocklists as
ready-made RPZ zone files — `$TTL`, `SOA`, `NS` and `CNAME .` (NXDOMAIN) records
— so there is no hosts-file conversion step and no generator script to maintain.

| Variable | Default | Purpose |
|----------|---------|---------|
| `bind_rpz_enabled` | `false` | Master switch |
| `bind_rpz_zones` | HaGeZi Multi Normal | `name` (zone origin) + `url` per blocklist, in precedence order |
| `bind_rpz_allowlist_extra` | `[]` | Domains to never block |
| `bind_rpz_allowlist` | internal domain + DNAME aliases + `_extra` | Full allowlist; override only to drop the protected defaults |
| `bind_rpz_refresh_schedule` | `daily` | systemd `OnCalendar` for the refresh timer |
| `bind_rpz_min_bytes` | `100000` | Smallest plausible blocklist; anything less is rejected |
| `bind_rpz_dir` | `/etc/bind/zones/rpz` | Where policy zones live |
| `bind_rpz_log_file` | `/var/log/named/rpz.log` | Blocked-query log |

### Blocklist tiers

All at `https://raw.githubusercontent.com/hagezi/dns-blocklists/main/rpz/`:

| File | Domains | Blocking level |
|------|---------|----------------|
| `light.txt` | ~42k | Relaxed — least likely to break anything |
| `multi.txt` | ~181k | Balanced. The default |
| `pro.txt` | ~216k | More aggressive telemetry blocking |
| `pro.plus.txt` | ~239k | Aggressive |
| `ultimate.txt` | ~269k | Maximum |
| `tif.mini.txt` | — | Malware/phishing threat intel; layer *alongside* a tier, not instead of one |

If `raw.githubusercontent.com` is unreachable, the same paths exist under
`https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/rpz/`.

Adding a second list is just another entry in `bind_rpz_zones`. Ordering is
meaningful: zones are consulted in the order listed, and the local allowlist is
always inserted first.

### Allowlisting a false positive

Add the domain to `bind_rpz_allowlist_extra` in host_vars and re-run the role.
It is rendered into a local `rpz.allowlist` policy zone as an `rpz-passthru`
record covering both the domain and everything beneath it, and that zone is
listed first, so it beats every blocklist. Do not edit the zone file on the
host — it is regenerated on each run.

To find out *why* something is broken, the RPZ log names the exact rule:

```
rpz: client 192.168.1.50#41439 (doubleclickbygoogle.com): rpz QNAME NXDOMAIN
     rewrite doubleclickbygoogle.com/A/IN via doubleclickbygoogle.com.rpz.hagezi-multi
```

### Refreshing

`bind-rpz-refresh.timer` runs `/usr/local/sbin/bind-rpz-refresh` daily. Per list
it does a conditional GET (so an unchanged list transfers nothing), rejects an
implausibly small body, runs `named-checkzone`, and only then installs the file
and does `rndc reload <zone>` — a reload rather than a restart, so the resolver
cache survives. **Nothing is installed until it validates**, so a truncated or
corrupted download leaves the previous good blocklist in place.

> Reloaded rules take up to a minute to bite: named rebuilds the RPZ summary
> database no more often than `min-update-interval` (60s by default). A domain
> that is still resolving right after a refresh is almost certainly this, not a
> failed reload — `rndc zonestatus <zone>` shows whether the zone itself loaded.

The role runs the same script once before templating `named.conf.options`,
because named refuses to load a policy zone whose file is missing. A refresh
failure only fails the play while a zone has no file yet; after that a transient
upstream outage just means a stale list, and the timer is what surfaces it:

```bash
systemctl status bind-rpz-refresh.service
journalctl -u bind-rpz-refresh
```

### Costs

Loading Multi Normal takes named's RSS to roughly 250 MB and adds ~2s to
startup. Fine on bertha (4 GB); check before enabling on anything smaller.

**Per view.** With `bind_views_enabled` the policy zones are loaded once in each
view, so two views means roughly 500 MB. Unlike the reverse and DNAME zones they
cannot be shared with `in-view`: named rejects an in-view reference as a
response-policy target —

```
named.conf.options:203: response-policy zone 'rpz.allowlist' for view internal
  is not a primary or secondary zone
```

Still comfortable on bertha, but it is the reason to drop to `light.txt` rather
than reach for `pro.txt` on a box with views enabled.

That per-view loading is also why `bind-rpz-refresh` issues one
`rndc reload <zone> IN <view>` per view. The bare `rndc reload <zone>` the
script used before views existed now fails outright — `zone was found in
multiple views` — and reloading only one view would leave the other serving
yesterday's blocklist.

This is just personal stuff. Not for use by anyone, etc.
