# DNS server for home network

This role builds on [BIND9](https://www.isc.org/bind/) (a deliberately hard way to do DNS). It reads the Ansible inventory data and creates [DNS zone files](https://en.wikipedia.org/wiki/Zone_file) from it.

This role:

* Installs and configures BIND.
* Gathers information about machines in the Ansible inventory.
* Assigns inventory FQDNs to inventory IP addresses.
* Finds application CNAMEs and maps them to inventory FQDNs.
* Publishes each host's Tailscale address under a `ts.` name.
* Generates zone files, both normal and reverse.

This setup also allows an external DHCP server to make changes, through [DDNS](https://en.wikipedia.org/wiki/Dynamic_DNS).

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
`host_vars`. The [`network-tailscale-address`](../network-tailscale-address/README.md)
role holds the device to this address. This role publishes the address
alongside the LAN A record, so each host has a name for both paths to it:

```text
server-64gb-storage.kberg.ber                IN  A  192.168.1.116
ts.server-64gb-storage.kberg.ber             IN  A  100.80.1.116
```

This is the addressable form of "everything is accessed through Tailscale". A
composition on one host can reach a service on another host, over the tailnet,
by name. This is better than a hardcoded `100.x` address, which changes the
next time a device re-enrolls.

| Variable | Default | Purpose |
|----------|---------|---------|
| `bind_tailscale_records_enabled` | `true` | Whether the role publishes the `ts.` A records |
| `bind_tailscale_record_prefix` | `ts` | Label prefixed to `host_pfqdn` |

The role skips hosts without `host_tailscale_ipv4`. It does not generate PTR
records, because Tailscale addresses reverse under `100.in-addr.arpa`. This
role does not serve that zone, and MagicDNS already covers it.

## DNS filtering (Response Policy Zones)

This is optional Pi-hole-style ad and tracker blocking, done natively in BIND.
This avoids adding a second resolver to the network. The feature is off
unless `bind_rpz_enabled: true`. When off, the rendered config is
byte-identical to a build without this feature.

[HaGeZi](https://github.com/hagezi/dns-blocklists) publishes its blocklists as
ready-made RPZ zone files (`$TTL`, `SOA`, `NS`, and `CNAME .` / NXDOMAIN
records). As a result, this role needs no hosts-file conversion step and no
generator script.

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

To add a second list, add another entry to `bind_rpz_zones`. Order matters:
the role checks zones in the order listed, and it always inserts the local
allowlist first.

### Allowlisting a false positive

Add the domain to `bind_rpz_allowlist_extra` in host_vars, then run the role
again. The role renders this into a local `rpz.allowlist` policy zone, as an
`rpz-passthru` record that covers the domain and everything beneath it. This
zone is listed first, so it takes priority over every blocklist. Do not edit
the zone file on the host, because the role regenerates it on each run.

To find out *why* something is broken, the RPZ log names the exact rule:

```
rpz: client 192.168.1.50#41439 (doubleclickbygoogle.com): rpz QNAME NXDOMAIN
     rewrite doubleclickbygoogle.com/A/IN via doubleclickbygoogle.com.rpz.hagezi-multi
```

### Refreshing

`bind-rpz-refresh.timer` runs `/usr/local/sbin/bind-rpz-refresh` daily. For
each list, the script does a conditional GET, so an unchanged list transfers
nothing. It rejects a body that is implausibly small, then runs
`named-checkzone`. Only after these checks pass does it install the file and
run `rndc reload <zone>`. A reload, not a restart, keeps the resolver cache
intact. **The role installs nothing until it validates the file**, so a
truncated or corrupted download leaves the previous good blocklist in place.

> A reloaded rule can take up to a minute to take effect. named rebuilds the
> RPZ summary database no more often than `min-update-interval` (60 seconds by
> default). If a domain still resolves right after a refresh, this delay is
> the most likely cause, not a failed reload. Run `rndc zonestatus <zone>` to
> check whether the zone itself loaded.

The role runs the same script once, before it templates `named.conf.options`,
because named refuses to load a policy zone with a missing file. A refresh
failure only fails the play while a zone has no file yet. After that, a
temporary upstream outage only leaves a stale list, and the timer is what
surfaces it:

```bash
systemctl status bind-rpz-refresh.service
journalctl -u bind-rpz-refresh
```

### Costs

Loading Multi Normal raises named's RSS to about 250 MB, and adds about 2
seconds to startup. This is fine on bertha (4 GB). Check the available memory
before you enable this on a smaller host.

This role is for personal use only. It is not intended for other people.
