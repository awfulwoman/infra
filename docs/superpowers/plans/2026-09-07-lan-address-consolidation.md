# LAN address consolidation — themed static blocks below .100, DHCP pool .100–.250

> Revised after review. The first draft asserted that a dhcpd `host` declaration
> protects an address inside a `range`; it does not (see "What actually protects an
> address"). The cutover order, the dependency list and the device counts have all
> changed as a result.

## Context

Static addresses on `192.168.1.0/24` have drifted into the DHCP pool. The pool is
`192.168.1.100–199` (`roles/infra-dhcpd/defaults/main.yaml`, not overridden anywhere),
and **9 inventory-assigned addresses sit inside it**: `.111 .116 .117 .118 .120 .130
.140 .141 .171`.

This is not theoretical. On bertha's lease file:

- **`.120` is an ACTIVE lease to `ce:a9:da:af:7d:71` ("OnePlus-6")** while
  `minipc-8gb-camina` holds it statically. Bertha's own neighbour table resolves `.120`
  to the phone, and `ssh 192.168.1.120` returns `Connection reset`.
- `.118` (`server-8gb-backups`) has been leased to `6c:1f:f7:6e:5e:35`.
- Camina's MAC (`6c:2b:59:65:a8:53`) holds leases at `.139` and `.174`; malcolm's
  (`1c:f6:4c:3e:51:a5`) at `.121` — managed hosts are both losing their statics and
  taking dynamic addresses.

Intended outcome: every static address below `.100`, grouped by role; the dynamic pool
occupying `.100–.250`; and the address-space separation documented so the drift cannot
silently recur.

## What actually protects an address

**Only keeping it out of the `range`.** A `host` declaration does not.

ISC dhcpd excludes `fixed-address6` from `range6`, and says so in `man 5 dhcpd.conf`
(line 1227 on bertha). The IPv4 `range` section says nothing of the kind — the asymmetry
is deliberate. ISC's own shipped example is explicit
(`/usr/share/doc/isc-dhcp-server/dhcpd.conf.example:75-76`):

> Fixed IP addresses can also be specified for hosts. These addresses should not also be
> listed as being available for dynamic assignment.

A `host` declaration steers only the client whose MAC matches it. Allocation for every
other client comes from the `range` free-list, which never consults `fixed-address`.

Proven on this network: both access points have had `fixed-address` reservations inside
the pool for as long as the config has existed, are up, and have **never** been issued a
lease (`grep -c` over `dhcpd.leases` → `0`). They are on-device static. The reservation
reserved nothing.

**Consequence:** the reservations in change 1 below are worth having — they are correct,
they matter for hosts that genuinely DHCP, and they are useful inventory-driven
documentation — but they are *not* a safety mechanism, and nothing in the cutover may be
sequenced as though they were.

## Constraints

**The tailnet octet invariant, which is already broken.** `docs/networking.md` documents
`192.168.1.X` ⇒ `100.80.1.X`. Live `tailscale status` disagrees with inventory on several
hosts: `deedee` is on `100.78.236.118` (not `.2`), `test-router` on `100.109.31.2` (not
`.221`), `albion` on `100.89.37.34`; `backups` and `norman` are not enrolled at all.
Because `bind_split_horizon_enabled: true`, the `tailscale` view publishes
`host_tailscale_ipv4` verbatim, so tailnet queries for deedee already resolve to an
address nobody holds. All eight target addresses (`100.80.1.{11,20,21,22,23,24,25,29}`)
are confirmed free. Fix or explicitly exempt the drifted hosts before renumbering on top
of a broken baseline.

**`bind_default_ttl` is 604800 — one week** (`roles/infra-named/defaults/main.yaml:2`).
Bertha is authoritative so it won't cache its own data, but every consumer will:
systemd-resolved on each host, macOS `mDNSResponder`, Docker's embedded resolver,
Traefik, browsers. Without action, old addresses stay cached for seven days after
cutover. This is more likely to cause trouble than netplan.

## Target scheme

| Block | Purpose |
|---|---|
| `.1–.9` | Core routing & DNS |
| `.10–.19` | Out-of-band and non-Ansible appliances |
| `.20–.49` | Ansible-managed servers |
| `.50–.69` | Network gear (APs, switches) |
| `.70–.99` | Fixed IoT, voice satellites, ESPHome, spare |
| `.100–.250` | **DHCP dynamic pool** (151 addresses) |
| `.251–.254` | Reserved |

Sized from measurement: 40 lease blocks, 39 distinct addresses, 13 currently active, 0
abandoned, and 19 of the 39 MACs locally-administered (randomised privacy MACs). A 51-
address pool would have run at ~76% lifetime utilisation; 151 leaves real headroom.
Address stability matters here because WatchYourLAN and the Uptime Kuma ping monitors
(`roles/composition-uptime-kuma/tasks/main.yaml:61`) identify devices by address.

## Assignments

**Core `.1–.9`** — no change: bertha `.1`, deedee `.2`, randolph `.3`, norman `.4`

**Appliances `.10–.19`**

| Device | From | To | Tailnet |
|---|---|---|---|
| kvm-tesmart-8port | `.10` | `.10` (no change) | — |
| raspberry-pi4-2gb-pikvm | `.111` | `.11` | `100.80.1.11` |
| esphome kc868-a16 | `.15` | `.15` (no change) | — |

**Servers `.20–.49`**

| Host | From | To | Tailnet |
|---|---|---|---|
| server-64gb-storage | `.116` | `.20` | `100.80.1.20` |
| server-8gb-backups | `.118` | `.21` | `100.80.1.21` |
| minipc-8gb-homebrain | `.130` | `.22` | `100.80.1.22` |
| minipc-8gb-camina | `.120` | `.23` | `100.80.1.23` |
| raspberry-pi5-4gb-belinda | `.117` | `.24` | `100.80.1.24` |
| apple-macmini-m4-16gb-malcolm | `.99` | `.25` | `100.80.1.25` |
| minipc-8gb-test-router | `.221` | `.29` | `100.80.1.29` |

**Network gear `.50–.69`**: ap-livingroom `.140`→`.50`, ap-pantry `.141`→`.51`

**IoT & satellites `.70–.99`**: ha-voice bedroom `.248`→`.70`, kitchen `.210`→`.71`,
livingroom `.220`→`.72`, charlie `.171`→`.73`

**14 devices move**; 8 need `host_vars` edits (the 7 servers **plus pikvm**, which has no
network role but still carries `host_ipv4`/`host_tailscale_ipv4` at
`inventory/host_vars/raspberry-pi4-2gb-pikvm/core.yaml:19,22`).

`vps-hetzner-public01` (`188.245.37.81`) is not on the LAN and does not move.

**Unowned address to identify first:** `192.168.1.98` is live (`34:94:54:74:3f:08`,
REACHABLE, answers ping), absent from all inventory, and has never been leased — another
on-device static. It falls inside the new `.70–.99` block. Identify it and add it to
`hosts-unmanaged.yaml` before someone hands `.98` out by hand.

## Missing data to collect first

Three managed hosts have no `host_mac`. Two recovered from bertha's neighbour table:

- `raspberry-pi4-2gb-pikvm` → `e4:5f:01:7e:55:51`
- `raspberry-pi5-4gb-belinda` → `2c:cf:67:22:a5:91`
- `minipc-8gb-test-router` → **not in ARP; offline ~46 days.** Collect when powered.

Also record the KC868-A16's MAC, and `unmanaged-kvm-tesmart-8port`'s (on-device static
at `.10`, so no reservation is possible without it).

## Changes

### 1. Validate the dhcpd config before restarting — `roles/infra-dhcpd/tasks/main.yaml`

The deploy task templates the config and `notify: Restart dhcpd` in the same run, so an
invalid config takes DHCP off the LAN. `infra-named` already does this correctly
(`roles/infra-named/tasks/main.yaml:267` uses `validate: named-checkzone …`).

Add `validate: dhcpd -t -cf %s` to "Deploy dhcpd configuration". Confirmed to work
unprivileged on bertha (`dhcpd -t -cf /etc/dhcp/dhcpd.conf` → exit 0). **Do this first**,
before any other dhcpd change.

### 2. Reserve managed hosts too — `roles/infra-dhcpd/templates/dhcpd.conf.j2`

Add a loop over `groups['infra']` alongside the existing `unmanaged` loop, reusing its
guard (`h.get('host_ipv4') and h.get('host_mac')`). Exclude `inventory_hostname` so
bertha does not emit a declaration for its own LAN NIC.

Correctness and documentation only — per "What actually protects an address" this is not
a safety mechanism. A LAN-subnet guard here is defensive rather than a live fix:
`vps-hetzner-public01` has no `host_mac`, so the existing guard already excludes it.

### 3. Pool bounds — `roles/infra-dhcpd/defaults/main.yaml`

`dhcpd_range_start: 192.168.1.100` (unchanged), `dhcpd_range_end: 192.168.1.250`.

Also fix `roles/infra-dhcpd/README.md:16`, which documents the `dhcpd_dns_servers`
default as `["192.168.1.2"]`; it is actually `[192.168.1.1, 8.8.8.8]`.

### 4. De-hardcode every address reference **before** anything moves

This is the highest-leverage change: once each reference derives from inventory, the
renumber propagates on redeploy instead of needing a synchronised edit.

| File | Now | Change |
|---|---|---|
| `roles/client-nut/templates/upsmon.conf:3` | `eaton@192.168.1.130` | → `hostvars['minipc-8gb-homebrain'].host_ipv4`. **Missed in the first draft** — the file has no `.j2` extension so a `--include` grep skips it. `client-nut` runs on backups, belinda and storage; break this and none of them shut down cleanly on a power cut. |
| `roles/composition-homepage/templates/services.yaml:85` | `.116:8000` | → inventory reference |
| `roles/composition-homepage/templates/docker.yaml:4` | `.130:2375` | → inventory reference. Note this is an **unauthenticated Docker socket** — if `.130` is reissued to a stranger's device mid-cutover, homepage talks to it. |
| `roles/composition-homepage/templates/docker.yaml:7` | `.112:2375` (`mqtt-docker`) | **Stale** — `.112` is not in inventory and ARP shows a randomised-MAC Apple device there. Delete the entry. |
| `roles/composition-reverseproxy/templates/providers/{homeassistant,watchyourlan,esphome}.yaml` | `.130:{8123,8840,6052}` | → inventory reference |
| `roles/composition-reverseproxy/templates/providers/musicassistant.yaml:50` | `.116:8095` | → inventory reference |

**Variable-derived references that a literal-IP grep cannot see** — these follow the
inventory automatically but still require a redeploy on the right host:

- `roles/backups-zfs-server/tasks/main.yaml:194,195` — `known_hosts` keyed on
  `hostvars[item].ansible_host`, with `ignore_errors: true` at `:199` so failure is
  **silent**; `:230` — the generated pull script embeds `--host {{ ansible_host }}`.
  Re-run `backups-zfs-server` on **both** `server-8gb-backups` and
  `raspberry-pi5-4gb-belinda`, and prune stale entries from their `/root/.ssh/known_hosts`.
- `roles/composition-reverseproxy/templates/providers/gotosocial.yaml:44` and
  `personalsite.yaml:53` — both pin
  `hostvars['server-64gb-storage'].host_tailscale_ipv4` and render on
  **`vps-hetzner-public01`**. Public-facing GoToSocial and the personal site go down
  until the VPS is redeployed. Sequence this immediately after storage's tailnet change.
- `roles/composition-homeassistant/templates/ha/configuration.yaml:47,58` — Wake-on-LAN
  `host:` for storage and backups. Needs an HA restart or the WOL switches misreport.
- `roles/composition-uptime-kuma/tasks/main.yaml:61` — ping monitors keyed to
  `host_ipv4`, synced by `host_name_short`. Verify the sync reports *updated*, not
  *created*, or you get duplicate monitors.

### 5. LAN-subnet guard in `roles/infra-named/templates/db.reverse.zone`

The managed-host PTR loop has no subnet check, which is why
`dig +short 81.37.168.192.in-addr.arpa PTR @192.168.1.1` returns
`vps-hetzner-public01.cloud.hetzner.ewwww.eu.` — a PTR for `192.168.37.81`, an address
that does not exist.

Guard against **`bind_iprange_segment` as a /16** (`192.168.0.0/16`,
`roles/infra-named/defaults/main.yaml:44`) — *not* `dhcpd_subnet`, which the first draft
specified. `infra-named` has no `dhcpd_*` variables in scope. `netaddr` and
`ansible.utils` are installed, so `ipaddr` filters are available.

### 6. Docs

`docs/networking.md` (block table; its worked examples still use `storage .116` /
`malcolm .99`), plus three files the first draft missed entirely: `docs/hosts.md:9-15`
(full host/address table), `docs/wifi.md:14,15,30` (AP addresses), `docs/router.md:162,
181,183` (dhcpd/DNS narrative), and `roles/infra-named/README.md:35,50,51` (worked
examples on `.116`). Regenerate `docs/snapshots/domains-{lan,remote}.json` via
`scripts/snapshot-domains.sh` afterwards.

## Cutover order

The pool starts at `.100` and stays there, so **widening it to `.250` must come last** —
doing it early would pull `.210/.220/.221/.248` into the pool rather than protecting
anything. Everything vacates the pool range first; the pool grows into the space they
leave.

**T-7 days — TTL.** Set `bind_default_ttl: 300`, deploy `infra-named`. Nothing else can
safely proceed until the old week-long TTL has aged out of every consumer's cache.

**T-1 day — lease time.** Drop `dhcpd_default_lease_time`/`dhcpd_max_lease_time`
(`roles/infra-dhcpd/defaults/main.yaml:14-15`) from `86400` to `600`, deploy, let clients
converge. This is what actually shortens the tail — **not** clearing
`/var/lib/dhcp/dhcpd.leases`, which the first draft suggested. Clearing the server's
database does not make a client release anything (the client keeps its address until its
own T1/T2 fires), dhcpd refuses to start if the file is absent, and wiping it destroys
the record of currently-active leases so the same address can go to two clients. Leave
the lease file alone.

**Step 1 — hygiene, no addresses move.** Changes 1, 2, 4 and 5 above, plus the recovered
MACs. Verify `dhcpd -t` passes and `named-checkzone` is clean. Redeploy the dependents
touched in change 4 so they are running on inventory-derived addresses *before* those
addresses change.

**Step 2 — clear the future pool range.** Move the four devices sitting in `.200–.250`:
the three HA voice satellites (`.210/.220/.248` → `.71/.72/.70`) and `test-router`
(`.221` → `.29`). Satellites are dhcpd-side changes plus a device renew; test-router is
offline, so simply edit inventory.

**Step 3 — clear the current pool range**, in this order:

1. **camina** (`.120` → `.23`) — clears the live conflict. **Reach it at
   `100.80.1.120`, not `192.168.1.120`**: the phone currently answers ARP for that
   address. Note `roles/network-tailscale-address/tasks/main.yaml:77-78` warns that
   reassigning drops every connection to the host *including an Ansible connection over
   the tailnet* — so camina's LAN renumber and its tailnet renumber must be two runs.
2. **belinda** (`.117` → `.24`), **backups** (`.118` → `.21`)
3. **APs** (`.140/.141` → `.50/.51`) — these are **OpenWrt and on-device static**
   (`docs/wifi.md:14`), so this is `uci set network.lan.ipaddr` on each unit, done
   *before* the inventory edit, and it drops your management session. Do them
   separately: `docs/wifi.md:15` notes the pantry unit is the only 2.4 GHz radio
   reaching the living-room ESP32s.
4. **sat-charlie** (`.171` → `.73`)
5. **storage** (`.116` → `.20`), then **homebrain** (`.130` → `.22`) — highest blast
   radius, and homebrain's move is what breaks `client-nut` on three hosts if change 4
   was skipped
6. **malcolm** (`.99` → `.25`)
7. **pikvm last** (`.111` → `.11`) — it is the out-of-band recovery path for everything
   above. **Keep it on-device static**; the first draft proposed converting it to a DHCP
   reservation, which would make the recovery device depend on the service being
   changed. PiKVM uses systemd-networkd (not netplan) on a read-only root — remount `rw`
   before editing.

**Step 4 — widen the pool** to `.100–.250` and restore `dhcpd_default_lease_time`.

**Step 5 — restore `bind_default_ttl`**, redeploy `infra-named`, update docs, regenerate
snapshots.

### Per-host renumber recipe

`ansible_host: "{{ host_ipv4 }}"` on every managed host, so editing `host_ipv4` retargets
Ansible at an address the host does not have yet. Rather than the first draft's
`-e ansible_host=<OLD_IP>` (which works, but hangs at `netplan apply` until SSH timeout
and cannot distinguish "applied and dropped" from "died half-configured"), use the
role's existing `host_ipv4_extra`, which `roles/network-netplan/tasks/main.yaml:17`
composes as `[host_ipv4/subnet] + host_ipv4_extra`:

1. Set `host_ipv4_extra: ["192.168.1.20/24"]`, leave `host_ipv4` alone. Run. **Adding an
   address does not drop the session.**
2. Verify `ssh 192.168.1.20`.
3. Flip `host_ipv4` to the new address, clear `host_ipv4_extra`, run with
   `-e ansible_host=<NEW_IP>`. Only the old address is removed — the session is already
   on the one that survives. **The connection never drops**, and step 2 is a rollback
   point.

Exceptions: **malcolm** uses `roles/network-macos-static`, where
`networksetup -setmanual` (`tasks/main.yaml:22-32`) applies instantly and kills the
session mid-role, so "Set static DNS servers" (`:34-42`) never runs and malcolm can be
left with no resolver — it must be re-run against the new address to complete. **pikvm**
has no network role at all. Do not rely on `network_netplan_auto_apply`
(`roles/network-netplan/defaults/main.yaml:41`): it is declared and **never referenced
anywhere** in the repo.

Do not run `scripts/run-core.sh` mid-cutover — it runs every host's `core.yaml` in
sequence. Confirm the deployed `automation-infra` scripts on camina and malcolm are
empty first (`automation_infra_playbooks` is `[]` today, and
`roles/automation-infra/templates/automation-infra.sh.j2:30,38` passes only
`inventory/hosts.yaml`, so `groups['unmanaged']` would not exist and the dhcpd/named
templates would fail if it ever ran).

## Verification

```bash
# Config validity, on bertha
dhcpd -t -cf /etc/dhcp/dhcpd.conf
named-checkzone 168.192.in-addr.arpa /etc/bind/zones/db.ewwww.eu.reverse.zone

# Reachability. Expect test-router (offline ~46d) and possibly backups to fail —
# that is pre-existing, not a cutover failure.
ansible -m ping infra

# Forward and reverse agree, exactly one PTR each.
# NOTE belinda's host_site is `kberg`, not `xberg` (inventory line 9) — a
# pre-existing typo that will look like a mismatch if you are not expecting it.
for ip in 1 2 3 4 10 11 15 20 21 22 23 24 25 29 50 51 70 71 72 73; do
  printf "%-6s " ".$ip"; dig +short -x 192.168.1.$ip @192.168.1.1
done

# The bogus public-IP PTR is gone
dig +short 81.37.168.192.in-addr.arpa PTR @192.168.1.1   # expect empty

# No ACTIVE lease outside the pool. Filter on binding state — dhcpd keeps `free`
# records for old addresses indefinitely, so a bare lease list always shows them.
ssh bertha 'awk "/^lease /{ip=\$2} /binding state active/{print ip}" /var/lib/dhcp/dhcpd.leases | sort -u'

# No static address falls inside .100-.250
ansible-inventory --list | python3 -c "
import json,sys; d=json.load(sys.stdin)
print([ (h, v['host_ipv4']) for h,v in d['_meta']['hostvars'].items()
        if v.get('host_ipv4') and str(v['host_ipv4']).startswith('192.168.1.')
        and 100 <= int(str(v['host_ipv4']).split('.')[3]) <= 250 ])"

# Tailnet invariant holds for the eight movers
for h in 11 20 21 22 23 24 25 29; do tailscale status | grep " 100.80.1.$h "; done
```

Then clear WatchYourLAN's cache on homebrain (`{{ composition_config }}/wyl`), restart
Home Assistant, and confirm Uptime Kuma shows *updated* rather than duplicate monitors.

## Risks

- **Step 3 is the dangerous one**, and pikvm is deliberately last because it is the
  recovery path for the hosts ahead of it. The `host_ipv4_extra` recipe removes most of
  the lock-out risk; malcolm and pikvm, which cannot use it, carry the residual.
- **Bertha is not renumbered** (`.1`), so gateway and resolver stay put throughout —
  clients never lose DNS or routing mid-cutover.
- **Suspend ZFS replication for the window** (`scripts/suspend-backups.sh`). Failures in
  `backups-zfs-server`'s `known_hosts` task are silenced by `ignore_errors: true`, so a
  broken replication path will not announce itself.
- **The week-long TTL is the sleeper risk.** If the T-7 step is skipped, hosts will
  resolve old addresses for days afterwards and the failures will look random.
