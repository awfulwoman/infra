# Bertha Router Hardening Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Do the tasks in the order given. Task 3 changes how every later deploy authenticates, so it goes last.

**Goal:** Remove the three highest-severity findings from the security review of `router-4gb-bertha` on 2026-09-04. The wildcard private key leaves the tailnet. IPv6 gets a firewall. A stolen SSH key no longer gives instant root.

**Scope:** Findings 1, 2 and 3 only. The review found nine. The other six are listed at the end of this plan.

**Tech stack:** Ansible, iptables, ip6tables, systemd, sudo

---

## Context

bertha is the home router at 192.168.1.1. It runs BIND, dhcpd, and the ACME client that issues the internal wildcard certificate for `ewwww.eu`. The IPv4 firewall is already good: the INPUT and FORWARD chains default to DROP, and the WAN side reaches nothing.

Three faults remain. Each one is independent of the other two.

| # | Fault | Severity |
|---|---|---|
| 1 | The wildcard TLS private key is downloadable by any tailnet device, with no authentication | High |
| 2 | IPv6 has no firewall at all. All three chains accept | Medium |
| 3 | The `awful` account has passwordless sudo, so one SSH key is root | Medium |

---

## Task 1: Remove the wildcard private key from the tailnet

`cert-distribution.service` runs `python3 -m http.server` on `100.80.1.1:8420`. It serves `/fastpool/acme/distribution`, which holds `*.ewwww.eu.key`. There is no authentication. The tailnet has 15 peers, and the Tailscale policy is still a single allow-all grant. One compromised phone or laptop is enough to read the key and impersonate every internal service.

### The host firewall cannot correct this fault

The obvious repair is a source-scoped iptables rule that permits port 8420 only from the eight consumer hosts. This does not work. The live INPUT chain starts like this:

```
-A INPUT -j ts-input
-A INPUT -i lo -j ACCEPT
...
-A ts-input -i tailscale0 -j ACCEPT
```

tailscaled owns the `ts-input` chain, and that chain accepts everything that arrives on `tailscale0`. The jump to it is rule 1. A rule added after the jump never runs for tailnet traffic. A rule inserted before the jump moves down again when tailscaled restarts, because tailscaled re-inserts its own jump at position 1. Source filtering here is not reliable.

### Design decision: the controller copies the bundle

The pull over HTTP gives no benefit that is worth this exposure.

Only camina and malcolm run `automation-infra`, and camina has no playbook list yet. No consumer refreshes its own certificate on a timer. Every consumer receives the bundle when the controller runs that consumer's playbook. A copy through the controller therefore keeps the same cadence, and the key moves over SSH instead of over unauthenticated HTTP.

The bundle files belong to `awful`, and `ansible_user` is `awful` on bertha. The read needs no `become`. This keeps Task 1 independent of Task 3.

Two alternatives were rejected. A bearer token adds a new secret to every consumer host and solves nothing that SSH does not already solve. Issue #275 (scoped Tailscale grants) is the correct long-term control. It is also a tailnet-wide policy change with real blast radius. This key does not need to wait for it.

### Steps

- [ ] **Step 1: Read the bundle from bertha instead of downloading it**
  In `roles/client-cert-distribution/tasks/main.yaml`, replace the two `ansible.builtin.get_url` tasks with a delegated read:
  ```yaml
  - name: Read the candidate bundle from the certificate host
    ansible.builtin.slurp:
      src: "{{ client_cert_distribution_source_dir }}/{{ client_cert_distribution_bundle_name }}.{{ item }}"
    delegate_to: "{{ client_cert_distribution_source_host }}"
    loop: [fullchain.crt, key]
    register: candidate_bundle
    no_log: true
  ```
  Then write both files with `ansible.builtin.copy` and `content:`, to the same `.fullchain.crt.new` and `.key.new` names the role uses today. Keep `no_log: true` on the key.

  Do not change the validation tasks. The role reads the `.new` files with `community.crypto.x509_certificate_info`, compares the public key fingerprints, and refuses a mismatch before it touches the installed bundle. That logic still applies, and it is the safety net for this task.

- [ ] **Step 2: Add the new variables**
  In `roles/client-cert-distribution/defaults/main.yaml`:
  ```yaml
  client_cert_distribution_source_host: router-4gb-bertha
  client_cert_distribution_source_dir: /fastpool/acme/distribution
  ```
  Remove `client_cert_distribution_server` and `client_cert_distribution_port`. Both are now unused.

- [ ] **Step 3: Retire the server role**
  Remove `server-cert-distribution` from `playbooks/hosts/router-4gb-bertha/core.yaml`. Then delete `roles/server-cert-distribution/`.

- [ ] **Step 4: Remove the service from bertha**
  Ansible does not remove a unit that no role manages, so do this once by hand:
  ```bash
  ssh bertha 'sudo systemctl disable --now cert-distribution.service && \
    sudo rm /etc/systemd/system/cert-distribution.service && \
    sudo systemctl daemon-reload'
  ```

- [ ] **Step 5: Correct the documentation**
  Update `roles/client-cert-distribution/README.md`. The "Design notes" section says that access control comes from the Tailscale bind. That statement is no longer true. Remove the row for the port from the variable table, and add the two new variables.

- [ ] **Step 6: Rotate the wildcard key**
  The key was served without authentication from 2026-08-07 to today. The tailnet holds only the user's own devices, so the risk is low, but a reissue is cheap.

  One CSR private key serves every certificate that this host issues (`/fastpool/acme/private/csr.key`). bertha issues one certificate, so the effect is limited to the wildcard.

  CAUTION: Let's Encrypt permits 5 duplicate certificates per week. One reissue is safe. Do not repeat this step in a loop.

  Remove the CSR key, the CSR, and the issued certificate. Then run the playbook with the `infra-certbot` tag. `infra-certbot` issues a new certificate when the certificate file is absent.

- [ ] **Step 7: Correct a dead guard in `infra-certbot`**
  `roles/infra-certbot/tasks/cert.yaml:13` reads:
  ```yaml
  path: "{{ infra_certbot_csr_private_key_filename }}/{{ infra_certbot_csr_private_key_filename }}"
  ```
  The first variable must be `infra_certbot_csr_private_key_dir`. The `stat` therefore always reports "absent", and the guard on the next task never holds. No damage results today, because `community.crypto.openssl_privatekey` with `state: present` is idempotent. Correct it while the rotation makes the code path fresh.

- [ ] **Step 8: Verify**
  ```bash
  # the service and the port are gone
  ssh bertha 'systemctl is-active cert-distribution'   # must print "inactive"
  ssh bertha 'ss -tlnp | grep 8420'                    # must print nothing

  # a consumer still receives a valid bundle
  ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags cert
  ssh storage 'sudo openssl x509 -noout -dates -in /etc/ssl/internal-wildcard/fullchain.crt'

  # the key on the consumer still pairs with the certificate
  ssh storage 'sudo openssl pkey -pubout -in /etc/ssl/internal-wildcard/privkey.key | sha256sum'
  ssh storage 'sudo openssl x509 -pubkey -noout -in /etc/ssl/internal-wildcard/fullchain.crt | sha256sum'
  ```
  Deploy the remaining seven consumers: randolph, belinda, backups, homebrain, camina, public01, deedee.

---

## Task 2: Filter IPv6

`ip6tables` has policy ACCEPT on INPUT, FORWARD and OUTPUT, and no rules of its own. `network-routing-basic` writes IPv4 rules only. sshd listens on `[::]:22`, so it is reachable over link-local IPv6 from the LAN and from the Fritz!Box segment. The claim that the WAN cannot reach the router holds for IPv4 only.

IPv6 forwarding is off, so there is no transit risk through the router.

Only bertha uses `network-routing-basic`. The blast radius of this task is one host.

### What must stay open

bertha has two IPv6 services. sshd listens on port 22. tailscaled listens on port 41641. BIND is configured with `listen-on-v6 { none; }`, and dhcpd runs with `-4`. The allow-list is therefore small.

CAUTION: Permit ICMPv6 before the INPUT policy becomes DROP. IPv6 uses ICMPv6 for neighbor discovery. A DROP policy without an ICMPv6 rule breaks the link to every LAN device.

### Steps

- [ ] **Step 1: Add the toggle**
  In `roles/network-routing-basic/defaults/main.yaml`:
  ```yaml
  # IPv6 firewall. Separate from network_routing_firewall so the v4 ruleset can
  # be trusted in production before the v6 one is turned on.
  network_routing_firewall_v6: false
  ```

- [ ] **Step 2: Write the IPv6 rules**
  Add `roles/network-routing-basic/tasks/firewall-v6.yaml`, included from `tasks/main.yaml` when `network_routing_firewall_v6` is true. Every task takes `ip_version: ipv6`. Add the ACCEPT rules first, and set the policies last, in the same order the IPv4 tasks use.

  | Order | Rule |
  |---|---|
  | 1 | `-i lo` ACCEPT |
  | 2 | `ctstate ESTABLISHED,RELATED` ACCEPT |
  | 3 | `protocol: icmpv6` ACCEPT |
  | 4 | `-i tailscale0` ACCEPT |
  | 5 | `-i {{ lan_iface }} -p tcp --dport 22` ACCEPT |
  | 6 | INPUT policy DROP |
  | 7 | FORWARD policy DROP |

  The existing `Save iptables rules` handler needs no change. `netfilter-persistent save` already writes `/etc/iptables/rules.v6`, and that file is present on bertha today.

- [ ] **Step 3: Hold IPv6 forwarding off**
  Add a sysctl task that sets `net.ipv6.conf.all.forwarding` to `0`. The value is already 0, but no role states it. This makes the intent explicit and survives a kernel default change.

- [ ] **Step 4: Turn it on for bertha**
  Add `network_routing_firewall_v6: true` to `inventory/host_vars/router-4gb-bertha/core.yaml`, next to `network_routing_firewall`.

- [ ] **Step 5: Deploy**
  ```bash
  ansible-playbook playbooks/hosts/router-4gb-bertha/core.yaml --tags network-routing-basic
  ```
  Ansible reaches bertha over IPv4, and `ansible_host` is `192.168.1.1`. An error in the IPv6 rules cannot stop the deploy or close the management path.

- [ ] **Step 6: Verify**
  ```bash
  # the ruleset is in place
  ssh bertha 'sudo ip6tables -S'

  # neighbor discovery still works — this is the rule that breaks first
  ssh bertha 'ping -6 -c2 ff02::2%enp1s0'

  # Tailscale still works over IPv6
  ssh bertha 'tailscale ping storage'

  # the rules survive a reboot
  ssh bertha 'sudo reboot'
  ssh bertha 'sudo ip6tables -S | grep -c DROP'
  ```
  If neighbor discovery fails, the ICMPv6 rule is absent or is placed after the policy change.

---

## Task 3: Require a password for sudo

`/etc/sudoers` holds `awful ALL=(ALL) NOPASSWD: ALL`. The vaulted `ansible_become_password` is therefore never used. Theft of one SSH key gives root on the router.

`roles/system-security/tasks/main.yaml:41` writes this line. The default that drives it is in `roles/system-security/defaults/main.yaml`:

```yaml
security_sudoers_passwordless:
  - "{{ vault_server_username }}"
security_sudoers_passworded: []
```

The mechanism for the change already exists. Both tasks use the regular expression `^{{ item }}` against `/etc/sudoers`, so the passworded task rewrites the same line in place. Move the user from one list to the other.

### Why this is safe on bertha

Four facts make bertha the correct host to start with.

The `awful` account has a usable password. `passwd -S awful` reports `P`, and the shadow entry holds a `$6$` hash. `ansible_become_password` is set to `{{ vault_password }}` in the host_vars of all 10 hosts, and each host defines `vault_password` in its own `vault_credentials.yaml`.

Nothing on bertha depends on passwordless sudo. bertha does not run `automation-infra`. `bind-rpz-refresh` runs as root under systemd and calls no `sudo`. `cert-distribution.service` runs as `awful` and calls no `sudo`, and Task 1 removes it.

Host_vars beat role defaults, so the override reaches the role. The `vars:` block on the `include_role` call sets `security_fail2ban_enabled` only. That block outranks host_vars, and the repo already records this trap in a comment, but it does not name the sudoers variables.

### A wrong password costs root, so the role must refuse the change

WARNING: If `vault_password` does not match the account password, sudo stops working and no remote path to root remains.

The root account is locked. `passwd -S root` reports `L`, and the shadow entry holds `*` in place of a hash. `PermitRootLogin` is `no`, and Tailscale SSH is off. Recovery from a wrong password needs the physical console.

The naive pre-flight gives a false pass. While `NOPASSWD` is still in place, `sudo -k; sudo -S -v` succeeds without ever reading the password from stdin. It cannot report whether the password is correct.

A hash comparison does report it. The shadow entry holds the salt, so `mkpasswd` can recompute the hash from the candidate password and compare the two strings. This runs before the change and needs no interactive shell.

NOTE: This check assumes local authentication against `/etc/shadow`. bertha uses local authentication. A host that authenticates sudo through LDAP or SSSD needs a different check.

### Steps

- [ ] **Step 1: Add the guard to `system-security`**
  The role must refuse to configure passworded sudo when the become password is wrong. Put the guard in the role, not in bertha's playbook, so it also protects the fleet rollout described at the end of this task.

  Add these tasks to `roles/system-security/tasks/main.yaml`, before the two sudoers tasks, with `when: security_sudoers_passworded | length > 0`:
  ```yaml
  - name: Make sure that mkpasswd is available for the become password check
    become: true
    ansible.builtin.apt:
      name: whois
      state: present

  - name: Compare the become password against the account password
    become: true
    ansible.builtin.shell:
      cmd: |
        set -eu
        hash=$(awk -F: -v u="{{ item }}" '$1==u{print $2}' /etc/shadow)
        case "$hash" in
          '$6$rounds='*) echo UNSUPPORTED_ROUNDS; exit 1 ;;
          '$6$'*) ;;
          *) echo UNSUPPORTED_HASH; exit 1 ;;
        esac
        salt=$(printf '%s' "$hash" | cut -d'$' -f3)
        [ "$(mkpasswd -m sha-512 -S "$salt" -s)" = "$hash" ] && echo MATCH || echo MISMATCH
      stdin: "{{ ansible_become_password }}"
    loop: "{{ security_sudoers_passworded }}"
    register: become_password_check
    changed_when: false
    no_log: true

  - name: Refuse passworded sudo when the become password does not match
    ansible.builtin.assert:
      that: "become_password_check.results | map(attribute='stdout') | select('equalto', 'MATCH') | list | length == security_sudoers_passworded | length"
      fail_msg: >-
        ansible_become_password does not match the account password on this host.
        Passworded sudo removes the last remote path to root. Correct
        vault_password before you run this role again.
  ```
  `mkpasswd` reads the password from stdin, so the password never appears in the argument list of a process. `no_log: true` keeps it out of the Ansible output.

- [ ] **Step 2: Move the user to the passworded list**
  In `inventory/host_vars/router-4gb-bertha/core.yaml`:
  ```yaml
  # Passworded sudo, not passwordless: an SSH key alone must not give root on
  # the router. ansible_become_password below supplies the password for Ansible.
  security_sudoers_passwordless: []
  security_sudoers_passworded:
    - "{{ vault_server_username }}"
  ```

- [ ] **Step 3: Do a dry run first**
  ```bash
  ansible-playbook playbooks/hosts/router-4gb-bertha/core.yaml \
    --tags bootstrap-ubuntu-server --check
  ```
  The guard from step 1 runs in check mode and reports `MATCH` or fails. If it fails, stop. Do not continue to step 4.

- [ ] **Step 4: Deploy**
  ```bash
  ansible-playbook playbooks/hosts/router-4gb-bertha/core.yaml --tags bootstrap-ubuntu-server
  ```

- [ ] **Step 5: Make sure that Ansible can still become root**
  ```bash
  ansible router-4gb-bertha -m ping --become
  ansible router-4gb-bertha -m shell -a 'grep awful /etc/sudoers' --become
  ```
  The second command must print `awful ALL=(ALL) ALL`.

- [ ] **Step 6: Make sure that passwordless sudo now fails**
  ```bash
  ssh bertha 'sudo -k; sudo -n true'    # must fail with "a password is required"
  ```

### Follow-on, not part of this task

The same change suits the other nine hosts. The guard in step 1 makes that rollout safe. The role now refuses the change on any host where the password does not match.

One risk remains for camina and malcolm. Both run `automation-infra`, which runs `ansible-playbook` as `awful` on a timer. That path needs a working become password on the host itself, from the local vault password file. Do a test on one of those two hosts before you change `roles/system-security/defaults/main.yaml` for the whole fleet.

For a host with no physical console, add a dead-man's switch on top of the guard. `systemd-run --on-active=10m` can restore the `NOPASSWD` line, and you cancel the timer after step 5 passes. The routing role already uses this pattern. The guard makes it unnecessary on bertha, which has a serial console.

---

## Order of work

1. **Task 1** first. It removes the highest-value secret from the network, and it needs no `become` on bertha.
2. **Task 2** second. It touches one role that only bertha uses, and Ansible connects over IPv4, so it cannot close the management path.
3. **Task 3** last. It changes how every later deploy authenticates. If it fails, no other task is blocked.

## Not in this plan

The review found six more faults. They are lower severity, and each one is independent of the three above.

| # | Fault | Note |
|---|---|---|
| 4 | Flat LAN. IoT devices share a segment with management | Needs VLANs. Depends on switch and AP support |
| 5 | Other LAN devices send router advertisements | The Living Room HomePod (`f4:34:f0:2e:f4:c3`) is a Thread border router. bertha ignores the advertisements. Other clients accept them |
| 6 | DNS zone transfers are open to the whole LAN and tailnet | Set `allow-transfer { none; }`. No secondary server exists |
| 7 | The router's own resolver can bypass BIND and the RPZ blocklist | Set `dhcp4-overrides: use-dns: false` on the WAN interface |
| 8 | No router sysctl hardening | `send_redirects=1`, `rp_filter=2`, `log_martians=0` |
| 9 | Unused services and packages run on a router | ModemManager, udisks2, multipathd, fwupd. dhcpd also lacks `authoritative` |

Issue #275 (scoped Tailscale grants) stays open and stays valuable. Task 1 removes the wildcard key from the tailnet, but every other service on the tailnet is still reachable by every device on it.
