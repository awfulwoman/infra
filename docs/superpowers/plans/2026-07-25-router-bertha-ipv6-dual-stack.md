# Router Bertha IPv6 Dual-Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `router-4gb-bertha`'s LAN real dual-stack IPv6 — a delegated `/64` from the upstream Fritz!Box via DHCPv6-PD, advertised to LAN clients via RA/SLAAC, firewalled with the same default-DROP posture as the existing IPv4 setup — without disturbing the existing IPv4 routing/DHCP/DNS that already works.

**Architecture:** netplan/systemd-networkd continue to own IPv4 on both NICs unchanged. A new `dhcpcd` instance, restricted to the WAN NIC (`enp2s0`) via `allowinterfaces`, requests a normal address (`ia_na`) plus a delegated prefix (`ia_pd`) that it assigns automatically onto the LAN NIC (`enp1s0`). A new `radvd` instance advertises that prefix to the LAN via SLAAC; a dhcpcd hook reloads radvd whenever the PD lease changes. `roles/network-routing-basic` is extended with an independently-toggled `network_routing_firewall_v6` mirroring the existing v4 firewall, plus WAN-side ICMPv6/DHCPv6 allowances that IPv6 needs to function at all under a default-DROP policy (RFC 4890) — this is not optional hardening, it's a functional requirement.

**Tech Stack:** Ansible, netplan (unchanged), dhcpcd (dhcpcd-base + dhcpcd packages, Ubuntu 24.04 Noble), radvd, `ansible.builtin.iptables` (`ip_version: ipv6` — no new collection needed, verified locally via `ansible-doc`).

**Why now / non-obvious context:** A live check of bertha found the WAN side already receives IPv6 via RA/SLAAC, including a routed `/56` summary via the Fritz!Box — the signature of a CPE that offers DHCPv6-PD to downstream routers. The same check found bertha's LAN interface was, accidentally, willing to accept router advertisements from another LAN device (NDP showed a neighbor marked "router", MAC `f4:34:f0:2e:f4:c3` — not actively exploited since `accept_ra` happens to be 0 right now, but a router must never learn routing info from its own clients). This plan's netplan changes close that gap as a side effect.

**Key constraint (verified via web research, not guessed):** netplan cannot express DHCPv6-PD — still-open Launchpad bug #1771886, true even on the installed netplan 1.1.2. systemd-networkd supports PD natively since systemd 250+, but netplan's generated `.network` files are the only one networkd applies per interface (first-match-wins, not merged) — hand-writing a competing file would silently disable netplan's own config for that NIC. `dhcpcd` + `radvd`, fully decoupled from netplan/networkd, is the standard community workaround for exactly this gap.

**Safety:** bertha is the box the operator depends on for their own connectivity while working on it. This repo's edit history already includes one incident on this exact host (an SSH-socket-pin change broke SSH, required a pre-staged `systemd-run --on-active` dead-man's-switch rollback) and one near-miss (a WAN/LAN NIC swap black-holed all outbound traffic). Every task below that can affect live forwarding/default routes goes out under that same dead-man's-switch pattern: stage a revert script, arm `systemd-run --on-active=180 <script>`, apply the change, verify end-to-end (including from a real LAN client), then cancel the timer. Phases are separate commits, each verified before the next begins — do not collapse them.

**Second-opinion review:** this plan was reviewed by an independent Opus pass focused specifically on technical correctness (dhcpcd syntax, package names, hook mechanics, firewall completeness) before being finalized. Two real blockers it caught are already folded into the tasks below (the anti-conflict mechanism, and WAN-side ICMPv6/DHCPv6 firewall allowances) — see the inline notes marked **(Opus correction)**.

---

## Task 1: Extend `network-routing-basic` for IPv6 forwarding + firewall

- [ ] In `roles/network-routing-basic/tasks/main.yaml`, immediately after the existing "Enable IP forwarding" task, add:

  ```yaml
  - name: Enable IPv6 forwarding
    become: true
    ansible.posix.sysctl:
      name: net.ipv6.conf.all.forwarding
      value: "1"
      sysctl_set: true
      reload: true
  ```

- [ ] After the existing v4 "Allow forwarding from LAN to WAN" / "Allow established/related return traffic WAN to LAN" tasks, add their v6 twins (unconditional, same as v4 — not gated on the firewall flag):

  ```yaml
  - name: Allow forwarding from LAN to WAN (v6)
    become: true
    ansible.builtin.iptables:
      ip_version: ipv6
      chain: FORWARD
      in_interface: "{{ lan_iface }}"
      out_interface: "{{ wan_iface }}"
      jump: ACCEPT
    notify: Save iptables rules

  - name: Allow established/related return traffic WAN to LAN (v6)
    become: true
    ansible.builtin.iptables:
      ip_version: ipv6
      chain: FORWARD
      in_interface: "{{ wan_iface }}"
      out_interface: "{{ lan_iface }}"
      ctstate: ESTABLISHED,RELATED
      jump: ACCEPT
    notify: Save iptables rules
  ```

  No v6 MASQUERADE task — IPv6 has no NAT. LAN devices get globally routable addresses directly from the delegated prefix, which means the FORWARD default-DROP (added below) is the *only* thing preventing every LAN device from being reachable from the whole internet. Note this in the role README as a v6-specific fact, not a copy-paste afterthought.

- [ ] Inside the existing firewall-hardening block (`when: network_routing_firewall`), add a **second, independently-gated** block using a new `network_routing_firewall_v6` flag. Mirror every existing v4 task (loopback / established+related / Tailscale / LAN-TCP-loop / LAN-UDP-loop) with `ip_version: ipv6` added; the ICMP task becomes `protocol: ipv6-icmp`.

  **(Opus correction — functional bug, not hardening nitpick):** a naive v4→v6 port that only allows ICMPv6 *from the LAN* breaks IPv6 entirely once INPUT defaults to DROP, because bertha's own control-plane traffic arrives on **WAN**, not LAN. Add two WAN-facing tasks in this same block, unconditional (not LAN-scoped):

  ```yaml
  - name: Allow INPUT ICMPv6 on WAN (required for IPv6 to function — RFC 4890)
    become: true
    ansible.builtin.iptables:
      ip_version: ipv6
      chain: INPUT
      in_interface: "{{ wan_iface }}"
      protocol: ipv6-icmp
      jump: ACCEPT
    notify: Save iptables rules

  - name: Allow INPUT DHCPv6 client traffic on WAN
    become: true
    ansible.builtin.iptables:
      ip_version: ipv6
      chain: INPUT
      in_interface: "{{ wan_iface }}"
      protocol: udp
      destination_port: "546"
      jump: ACCEPT
    notify: Save iptables rules
  ```

  Rationale: once `net.ipv6.conf.all.forwarding=1`, the kernel stops auto-accepting RAs — dhcpcd's own `ipv6rs` userspace RS/RA exchange becomes the *only* path for the router's default route and PD renewal, and it needs ICMPv6 (types 133/134 RA, 135/136 NDP, 2 Packet-Too-Big for PMTUD) let through on WAN. DHCPv6 client renewal is a plain UDP/546 socket, independently blocked by INPUT-DROP unless explicitly allowed.

  Keep the existing "Set FORWARD policy to DROP" / "Set INPUT policy to DROP" tasks last in the block, unchanged.

- [ ] In `roles/network-routing-basic/defaults/main.yaml`, add `network_routing_firewall_v6: false` next to the existing `network_routing_firewall: false` (same safety-default posture — installs nothing extra, just gates the block above). Reuse the existing `network_routing_input_tcp_ports` / `network_routing_input_udp_ports` — no new port-list vars needed.

- [ ] `handlers/main.yaml` needs no change — `netfilter-persistent save` already persists both `iptables` and `ip6tables` rule sets.

- [ ] Update (or create) `roles/network-routing-basic/README.md` documenting `network_routing_firewall_v6` and the "no NAT in v6, FORWARD-DROP is the only backstop" point.

---

## Task 2: New role `roles/network-dhcpcd6-pd/` — WAN-side DHCPv6-PD client

Standard small-daemon role shape, copied from `roles/infra-dhcpd/` (defaults/tasks/handlers/templates/README, safety-default-off).

- [ ] `defaults/main.yaml`:

  ```yaml
  dhcpcd6_pd_enabled: false
  dhcpcd6_pd_iaid: 1
  dhcpcd6_pd_sla_id: 0
  dhcpcd6_pd_prefix_len: 64
  dhcpcd6_pd_suffix: 1
  ```

  Reuses the host's existing `wan_iface` / `lan_iface` — no new interface vars.

- [ ] `tasks/main.yaml`: assert `wan_iface`/`lan_iface` are set → apt install `dhcpcd-base`, `dhcpcd` (confirmed correct package names for Ubuntu 24.04 Noble; `dhcpcd` is in universe — confirm it's enabled on bertha) → template `dhcpcd.conf` (notify Restart dhcpcd) → template the hook script → `ansible.builtin.systemd` task with `state`/`enabled` both derived from `dhcpcd6_pd_enabled`.

- [ ] `templates/dhcpcd.conf.j2`:

  ```
  noarp
  ipv6only
  option rapid_commit
  allowinterfaces {{ wan_iface }}
  nohook resolv.conf, hostname, ntp.conf, timesyncd.conf

  interface {{ wan_iface }}
      ipv6rs
      ia_na 1
      ia_pd {{ dhcpcd6_pd_iaid }} {{ lan_iface }}/{{ dhcpcd6_pd_sla_id }}/{{ dhcpcd6_pd_prefix_len }}/{{ dhcpcd6_pd_suffix }}
  ```

  - `ipv6only` is belt-and-suspenders: dhcpcd never touches IPv4 anywhere.
  - `allowinterfaces {{ wan_iface }}` **(Opus correction)** restricts dhcpcd to the WAN NIC only. The first draft of this plan used a `systemd` unit `ExecStart=` override to achieve this — **do not do that**: the packaged `dhcpcd.service` is `Type=forking` with a `PIDFile=`, and its real `ExecStart` is `/usr/sbin/dhcpcd -q -b`; an override that drops the `-b` flag makes systemd wait forever for a fork that never happens, hanging the unit to start-timeout. `allowinterfaces` in `dhcpcd.conf` achieves the same restriction with zero unit-file risk and can't drift out of sync with the packaged unit.
  - `nohook resolv.conf, hostname, ntp.conf, timesyncd.conf` **(Opus correction)** stops dhcpcd from clobbering DNS/hostname/time config that netplan/systemd-resolved already own on this host — the packaged dhcpcd unit runs these hooks by default.

- [ ] `templates/70-radvd-reload.j2` → deployed to `/usr/lib/dhcpcd/dhcpcd-hooks/70-radvd-reload` **(Opus correction: canonical Noble path, not `/lib/...` — that only works via the usrmerge symlink)**, mode `0755`:

  ```sh
  case "$reason" in
  BOUND6|RENEW6|REBIND6|REBOOT6|DELEGATED6)
      systemctl reload-or-restart radvd.service
      ;;
  esac
  ```

  No prefix templating needed — radvd's `prefix ::/64` auto-detects whatever address dhcpcd just placed on `lan_iface` via `getifaddrs()`. Confirmed real dhcpcd-run-hooks(8) reason strings.

- [ ] `handlers/main.yaml`: single handler `Restart dhcpcd` (`ansible.builtin.systemd: name: dhcpcd, state: restarted`).

- [ ] `README.md`: Key Variables table + Design Notes covering the netplan-can't-do-PD limitation and why `allowinterfaces` (not a unit override) is the anti-conflict mechanism.

---

## Task 3: New role `roles/network-radvd/` — LAN RA/SLAAC server

- [ ] `defaults/main.yaml`:

  ```yaml
  radvd_enabled: false
  radvd_min_interval: 30
  radvd_max_interval: 100
  radvd_rdnss_servers:
    - "2606:4700:4700::1111"
    - "2606:4700:4700::1001"
  ```

  RDNSS points at public Cloudflare resolvers for phase 1, deliberately not bertha's own delegated-block address: unlike `prefix ::/64`, RDNSS has no auto-detect, so self-hosting it would need the hook script to re-template and diff `radvd.conf` on every PD renewal for no phase-1 benefit (existing v4 split-horizon DNS keeps working over the dual-stack LAN regardless). Self-hosted v6 RDNSS + `bind_listen_on_v6` is a natural fast-follow once base dual-stack is proven — not blocking this work.

- [ ] `tasks/main.yaml`: apt install `radvd` → template `/etc/radvd.conf` (notify Restart radvd) → `ansible.builtin.systemd` task keyed off `radvd_enabled`.

- [ ] `templates/radvd.conf.j2`:

  ```
  interface {{ lan_iface }} {
      AdvSendAdvert on;
      MinRtrAdvInterval {{ radvd_min_interval }};
      MaxRtrAdvInterval {{ radvd_max_interval }};
      prefix ::/64 {
          AdvOnLink on;
          AdvAutonomous on;
      };
      RDNSS {{ radvd_rdnss_servers | join(' ') }} {
          AdvRDNSSLifetime 900;
      };
  };
  ```

- [ ] `handlers/main.yaml`: single handler `Restart radvd`.

- [ ] `README.md`, same shape as `infra-dhcpd/README.md`.

---

## Task 4: Wiring — playbook, host_vars, netplan

- [ ] In `playbooks/hosts/router-4gb-bertha/core.yaml`, insert `network-dhcpcd6-pd` and `network-radvd` immediately after `network-routing-basic`, tags matching role names.

- [ ] In `inventory/host_vars/router-4gb-bertha/core.yaml`, under `network_netplan_config.ethernets`, add to **both** `enp2s0` and `enp1s0`:

  ```yaml
  accept-ra: false
  dhcp6: false
  ```

  This hands v6 on both NICs fully to dhcpcd/radvd, and closes the rogue-RA-acceptance finding on the LAN side as a side effect.

- [ ] Add `dhcpcd6_pd_enabled` / `radvd_enabled` and `network_routing_firewall_v6` to the same file, **but do not set them to `true` in the same commit as the netplan changes** — see phased rollout below.

- [ ] Run `pre-commit run --files <changed files>` before each commit; fix any failures before proceeding.

---

## Phased rollout (each phase = its own commit + apply + verification, do not collapse)

- [ ] **Phase 1 — inert install.** Land all new role files and the playbook wiring with `dhcpcd6_pd_enabled: false`, `radvd_enabled: false`, `network_routing_firewall_v6: false`. Run a plain `ansible-playbook playbooks/hosts/router-4gb-bertha/core.yaml`. Verify: packages installed, `systemctl is-active dhcpcd radvd` on bertha reports `inactive` for both. Zero live-traffic risk — commit and move on.

- [ ] **Phase 2 — enable PD + RA (dead-man's-switch window).** Stage a revert script on bertha that: reapplies the prior netplan YAML (accept-ra/dhcp6 keys removed), stops dhcpcd and radvd, sets `net.ipv6.conf.all.forwarding=0`, flushes any v6 FORWARD/INPUT rules, runs `netplan apply`. Arm it with `systemd-run --on-active=180 <revert-script>`. Then: flip the netplan `accept-ra`/`dhcp6` keys, set `dhcpcd6_pd_enabled: true` and `radvd_enabled: true`, apply the v6-forwarding sysctl task and the two unconditional v6 FORWARD ACCEPT rules from Task 1 (**`network_routing_firewall_v6` stays `false` in this phase** — don't enable the firewall and PD in the same window). Verify:
  - `ip -6 addr show dev enp2s0` on bertha shows a PD-derived + `ia_na` address.
  - `ip -6 addr show dev enp1s0` shows the delegated `/64` address (ending `::1`).
  - `ip -6 route show` shows a default route via WAN and no more foreign-RA routes on LAN.
  - From a **real LAN client**: a global IPv6 address in the delegated prefix, `ping -6 -c3 2606:4700:4700::1111` succeeds, OS resolver shows the advertised RDNSS.
  Cancel the timer only after all of the above pass.

- [ ] **Phase 3 — enable the v6 firewall (separate dead-man's-switch window, only after Phase 2 has run stable for a while).** Stage a second revert script (set v6 FORWARD/INPUT policy back to ACCEPT, remove the restrictive rules, `netfilter-persistent save`). Arm `systemd-run --on-active=180`. Flip `network_routing_firewall_v6: true` alone. Verify the same LAN-client checks as Phase 2 still pass, **and** from outside the LAN (e.g. a phone on mobile data) confirm an unsolicited connection attempt to a LAN client's global v6 address is refused/dropped. Cancel the timer only after both checks pass.

---

## Plan self-review checklist

- [x] netplan's DHCPv6-PD limitation confirmed via web research, not assumed (Launchpad #1771886, still open).
- [x] `ansible.builtin.iptables`'s `ip_version: ipv6` parameter confirmed locally via `ansible-doc` — no new collection needed.
- [x] Anti-conflict mechanism uses `allowinterfaces` in `dhcpcd.conf`, not a fragile systemd `ExecStart=` override (Opus-caught blocker, corrected).
- [x] `nohook resolv.conf, hostname, ntp.conf, timesyncd.conf` prevents dhcpcd from fighting netplan/systemd-resolved for DNS/hostname/time (Opus-caught gap, corrected).
- [x] Hook script path is the canonical Noble path, not the usrmerge-symlink-dependent one (Opus-caught nit, corrected).
- [x] WAN-side ICMPv6 + DHCPv6/546 INPUT allowances are present in the Phase 3 firewall — without them IPv6 breaks entirely under INPUT-DROP, not just a hardening gap (Opus-caught blocker, corrected).
- [x] No NAT66 task added — IPv6 doesn't use NAT; FORWARD-DROP is correctly identified as the sole backstop.
- [x] `network_routing_firewall_v6` is independently toggleable from the existing v4 `network_routing_firewall`, same safety-default-`false` posture.
- [x] Every task that can affect live forwarding/default routes is explicitly scoped to a dead-man's-switch phase, matching the pattern already used successfully twice on this exact host this session.
- [x] Rogue LAN router-advertisement finding (`f4:34:f0:2e:f4:c3`) is closed as a side effect of `accept-ra: false` on `enp1s0`, called out explicitly rather than silently fixed.
