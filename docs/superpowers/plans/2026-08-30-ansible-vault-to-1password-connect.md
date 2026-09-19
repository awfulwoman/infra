# Ansible Vault to 1Password Connect Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Secrets live in 1Password, are fetched at runtime, and rotate without a commit. An agent can create and rotate a secret without ever seeing its plaintext.

**Architecture:** A custom lookup plugin resolves `vault_*` variables from 1Password Connect inline, preserving the existing `vault_` indirection layer so no consuming role changes. Connect moves onto a new dedicated control node and binds to loopback. Secret creation uses `onepassword.connect.generic_item` with server-side generation, so plaintext never enters a playbook, the repo, or an agent's context.

**Tech Stack:** Ansible, 1Password Connect REST API, `onepassword.connect` collection, Python (`urllib`, pytest)

---

## Context

Secrets currently live as ~110 `vault_*` variables across 56 Ansible Vault files, all protected by a single password in `/opt/ansible/.vaultpassword`. Rotation means editing ciphertext and committing it, and git history keeps every superseded secret forever.

1Password Connect is already deployed on `raspberry-pi4-4gb-randolph` at `https://connect.{{ domainname_infra }}`, with two working consumers (`composition-gateway`, `composition-finances`). The infrastructure exists; what is missing is a way to use it that does not require rewriting all ~40 consuming roles.

**Be honest about the size of the win.** The Connect token will live in the controller's environment, which is the same shape as the vault password file living on the controller: one secret on one box unlocks everything. What this migration actually buys is no ciphertext in git history, rotation without a commit, a 1Password audit log, and scoped revocable tokens. It is a workflow and hygiene improvement, not a step change in threat model.

**Two blockers this plan solves:**

1. The existing read pattern (`ansible.builtin.uri` + `delegate_to: localhost` + `set_fact`) only works inside a task. It cannot resolve a variable inline in `group_vars`, so migrating that way means restructuring every role that consumes a secret.
2. `scripts/op-infra-write.py:53-61` generates the password client-side in Python and then does `print(password)` to stdout. Any agent that runs it sees the secret in its tool output — the exact thing to avoid.

---

## Design decision: a lookup plugin preserves the existing indirection

The repo convention is that `vault_*` names live in vault files and roles dereference them (`paperless_ngx_db_password: "{{ vault_paperless_ngx_db_password }}"`). Keeping that layer means **migration is a one-line swap per secret, with no consuming role changes at all.**

```yaml
# before — inventory/group_vars/infra/vault_hetzner.yaml
vault_hetzner_api_key_rw: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          6533...

# after — inventory/group_vars/infra/onepassword_hetzner.yaml (plaintext, no ciphertext)
vault_hetzner_api_key_rw: "{{ lookup('onepassword_connect', 'group/infra/hetzner', 'hetzner_api_key_rw') }}"
```

All ~110 downstream references keep working untouched. This also covers the roles that skip the indirection and use `vault_*` directly in templates (`composition-homepage`, `composition-downloads`, `composition-esphome`, `system-msmtp`, `backups-zfs-client`, and ~15 others) — they need no edit either.

Lookups are lazy (evaluated only when the variable is actually used) and run on the controller, so the token never leaves the local machine.

## Design decision: one vault

Everything Ansible touches lives in **Infra** (`tsnrmqmuafgj2b5ajwykn7jwpi`). The Private vault stays personal and is out of scope for this migration.

An earlier draft split the two vaults by audience, with Private write-only for automation. That does not survive the actual secret list. Every app admin password — `paperless_ngx`, `pihole`, `grafana`, `qbittorrent`, `uptime_kuma`, `peekaping`, `pinepods`, `jarvis_editor` — is injected into its app by the composition role, so Ansible must **read** it. `vault_password` has 22 references. A write-only vault would hold almost nothing.

It also collided with the naming scheme below: `host/server-8gb-backups` would exist in both vaults (login in Private, ZFS passphrase in Infra), making `vault=` a footgun on every lookup.

The split conflated two separate things. **Your** access to a vault in the 1Password app is not the same as the **token's** scope. You can read Infra in the app whatever the machine token is allowed to do, so human-facing items lose nothing by living there. Set the `url` field on them so 1Password still autofills.

The vault UUID is committed in plaintext, consistent with `inventory/group_vars/infra/core.yaml:51`. A vault UUID is an identifier, not a credential; access is governed by the token.

## Design decision: storage mirrors the inventory

**File path = item title.** One mapping file per item, in the same directory as the vault file it replaces.

| Mapping file | 1Password item |
|---|---|
| `group_vars/infra/onepassword_hetzner.yaml` | `group/infra/hetzner` |
| `group_vars/infra/onepassword_composition_n8n.yaml` | `group/infra/composition-n8n` |
| `group_vars/sitedeployment/onepassword.yaml` | `group/sitedeployment` |
| `host_vars/server-64gb-storage/onepassword_matrix.yaml` | `host/server-64gb-storage/matrix` |
| `host_vars/minipc-8gb-agatha/onepassword_hermes_jarvis.yaml` | `host/minipc-8gb-agatha/hermes-jarvis` |
| `host_vars/raspberry-pi4-8gb-norman/onepassword_credentials.yaml` | `host/raspberry-pi4-8gb-norman` |

The map is mechanical in both directions, so a script can assert that every `vault_*` variable resolves to exactly one item and field, and that every item and field has a consumer. At ~110 secrets that check is worth more than pretty names.

Titles sort alphabetically in the 1Password app, so `group/…` and `host/…` cluster on their own. The cost of `/` is that `op://Infra/group/infra/hetzner/api_key_rw` is not a valid secret reference. `op` is not installed on the controller, so nothing in this repo uses that form.

**Roles are the subject segment, not a tier.** Under `group/infra/` the subject is the consuming role (`composition-n8n`, `system-msmtp`) when one role owns the secret, and the provider (`hetzner`, `tailscale`, `digitalocean`) when several roles share an account credential. There is no `role/` prefix — a role is never a variable scope in Ansible, so it cannot be a storage tier without misrepresenting precedence.

**Field label = the variable name minus the `vault_` prefix.** `vault_hetzner_api_key_rw` becomes field `hetzner_api_key_rw` on item `group/infra/hetzner`. This repeats the item title, but it is the only rule that is always defined — `vault_misc.yaml` and `vault_compositions.yaml` have no common stem to strip — and it makes the reverse lookup a plain grep. For a Login-category item, 1Password's built-in fields are already labelled `username` and `password`, which is exactly what `vault_server_username` and `vault_password` become, so `host/<name>` is a plain Login item with no custom fields.

**Tag every item** `ansible`, plus `host:<name>` or `group:<name>`, plus `role:<role>`. A title carries one dimension; tags carry the rest, so "everything norman needs" stays answerable for group-scoped secrets too.

**Scale:** ~58 items, ~110 fields. The largest is `group/infra/gateway` at 11 fields.

**Do not re-scope in the same pass.** Several compositions run on one host but keep their secrets in `group_vars/infra`. Tightening those to `host_vars` would change item titles *and* variable precedence together. Migrate at today's scope; tighten afterwards as a separate revertible commit.

## Design decision: generation never exposes plaintext

`onepassword.connect.generic_item` with `generate_value: on_create` asks **Connect** to generate the value server-side. The plaintext never enters the playbook, the repo, an agent's context, or stdout.

`on_create` is the correct default — `always` rotates on every run and breaks running services. Use `always` only in a deliberate, separately-invoked rotation playbook.

`include_symbols: false` is deliberate: these values land in `.environment_vars` files consumed by Docker Compose, where shell metacharacters cause quoting failures.

## Design decision: fail loudly

No caching, no fallback. Connect being unreachable must stop a run with an actionable message, never silently yield an empty secret — an empty secret writes a broken config file that looks like it succeeded.

---

## Task 1: Cleanup — fix existing defects first

These are live defects found while surveying the vault surface. Fixing them first shrinks the migration and avoids carrying bugs across.

- [ ] **Step 1: Fix the world-readable vault password file**
  `roles/ansible-pull/tasks/main.yaml:11-20` writes the vault password file at mode `0644` from `vault_ansible_password`, which is **undefined anywhere in the repo**. The line carries the comment `# eh oh no`. Change the mode to `0600` and either resolve the circularity (the vault password stored inside the vault) or remove the task.

- [ ] **Step 2: Stop echoing the vault password**
  `scripts/ansible-pull/bootstrap-ansible-ubuntu-server.sh:39` prints the vault password to stdout. Remove that line.

- [ ] **Step 3: Delete dead secrets with no consumers**
  `vault_obsidian_user`, `vault_obsidian_password`, `vault_amazon_locker_name_main`, `vault_claudecode_longlived_token`, `vault_tailscale_id`, `vault_zfsbackup_password`, and the already-commented `vault_vagrant_*`.

- [ ] **Step 4: Fix naming drifts**
  `vault_vane_searxng_secret_key` (referenced) vs `vault_searxng_secret_key` (defined); `vault_chives_telegram_chat_ids` (5 refs) vs `vault_chives_telegram_chat_id` (defined singular); plus the undefined-but-defaulted `vault_zfs_api_key` and `vault_grafana_admin_user`.

- [ ] **Step 5: Resolve `roles/*/vars/main.yaml` shadowing**
  `utility-ubuntu-cloud-init` and `utility-raspberry-pi-cloud-init` re-encrypt `vault_server_username`/`vault_server_password` at `vars/` precedence, overriding group_vars. Move to defaults or delete.

- [ ] **Step 6: Scrub a leaked ciphertext block**
  `docs/superpowers/plans/2026-04-14-tailscale-dynamic-authkey.md:273` contains a real-looking `vault_tailscale_authkey` block for a variable no longer in the inventory. Treat as leaked.

- [ ] **Step 7: Split the multi-subject vault files**
  The naming scheme needs one subject per file. Two files break that, and both are fixed by the same edit as the migration:
  - `vault_compositions.yaml` holds 17 variables for ~10 apps. Split into `composition-gitea`, `composition-karakeep`, `composition-pinepods`, `composition-pihole`, `composition-qbittorrent`, `composition-arr` (radarr/sonarr/prowlarr), `composition-finances` (firefly), `composition-grafana`, `composition-vikunja`.
  - `vault_karakeep.yaml` (`vault_karakeep_api`) and the karakeep variables inside `vault_compositions.yaml` describe one role — merge into a single `composition-karakeep`.

- [ ] **Step 8: Enumerate the wholly-encrypted `sitedeployment` file**
  `inventory/group_vars/sitedeployment/vault.yaml` is encrypted as a whole file, so its variable names are hidden. Only `vault_sitedeployer_user` and `vault_sitedeployer_publickey` are referenced anywhere in the repo. Decrypt it to confirm nothing else is inside before planning its item.

- [x] **Step 9: Confirm the `automation_infra_playbooks` deletion was deliberate** — moot. `automation-infra` is deleted (`7658f07c`); scheduled playbook runs are Semaphore templates on camina.

---

## Task 2: Provision a dedicated control node

Bring a spare 8GB minipc online as a dedicated control node that also hosts Connect. Secrets are then fetched over `http://127.0.0.1:8080` — no DNS, no TLS, no Traefik, no cert expiry, no network hop — and **Connect can never be less available than the controller itself.**

### Why a new box rather than an existing one

The choice is about failure domains, not specs:

| | randolph (Pi4) | **spare minipc** | storage (i5) | malcolm (M4) |
|---|---|---|---|---|
| RAM free | 2.7G, **no swap** | ~7G + 4G swap | 19G + 8G swap | ~7G of 16G |
| Disk | **SD card** | SATA SSD | NVMe | NVMe |
| Churn | idle | **dedicated** | 73 containers, monthly reboot | interactive, ollama pinned |
| Blast radius | low | **low** | **very high** | medium |
| Docker at boot | yes | **yes** | yes | no — needs auto-login |

storage has the best hardware by a wide margin, but it is the biggest deploy target in the fleet: making it the controller means a broken storage cannot be repaired with Ansible. randolph is disqualified by its SD-card root and 4GB with no swap. malcolm would need macOS auto-login — which FileVault disables outright, and which writes a reversibly-obfuscated login password to `/etc/kcpassword` — plus first-ever macOS support in the composition framework.

A control node should be small, boring, dedicated and low-churn: its job is to work *when other things are broken*. The Celeron J4105 is slow, but Claude Code spends most of its wall-clock waiting on the API rather than on local compute.

Every role needed is already proven on homebrain or malcolm. `system-claude` is already cross-platform — it has an `install-ubuntu.yaml`, and `system_claude_profile_file` resolves to `.bashrc` off Darwin.

### Steps

- [x] **Step 1: Add the host to the inventory** — camina, in `infra`, `ubuntu_servers` and `zfs`.
  `inventory/hosts.yaml` — add `minipc-8gb-<name>` to the `infra`, `ubuntu_servers` and `zfs` groups.

- [x] **Step 2: Write host_vars** — `inventory/host_vars/minipc-8gb-camina/`. `fastpool` is a stripe on the internal SATA SSD, after a rebuild onto a new disk; the host sits at `.23` per the LAN address plan.
  `inventory/host_vars/minipc-8gb-<name>/core.yaml` — identity block, static IP via `network_netplan_config`, a `zfs:` declaration for a `fastpool` stripe on the internal SATA SSD with a `compositions` dataset (copy homebrain's shape, `core.yaml:41-55`), and `compositions: [1password-connect]`. Using `fastpool` keeps the `compositions_dataset` default working unchanged.
  `inventory/host_vars/minipc-8gb-<name>/vault_credentials.yaml` — `vault_password`. Model on `minipc-8gb-test-router/`, the existing spare of this type.

- [x] **Step 3: Write the host playbook** — `playbooks/hosts/minipc-8gb-camina/core.yaml`. `system-repos` and `automation-infra` have since been deleted from the repo: scheduled playbook runs live in Semaphore (`composition-semaphore`), and `ansible-core` no longer needs a checkout on the host.
  `playbooks/hosts/minipc-8gb-<name>/core.yaml` — model on homebrain's, minus the home-automation roles, plus `ansible-core`, `system-repos`, `system-claude`, `automation-infra`.

- [ ] **Step 4: Bind Connect to loopback** — **deferred.** Connect moved to camina but kept its Traefik route and DNS name (`6ac888d2`): the consuming tasks use `delegate_to: localhost`, so the request comes from whichever machine runs the playbook, which today is usually malcolm. Loopback is a one-line change once Ansible actually runs from camina.
  `roles/composition-1password-connect/templates/docker-compose.yaml.j2` — replace the Traefik labels with `ports: ["127.0.0.1:8080:8080"]`. Drop `notify: Restart Traefik` from `tasks/main.yaml`.
  `roles/composition-1password-connect/defaults/main.yaml` — remove `composition_dns_subdomains: [connect]`; a loopback-only service wants no DNS record. This also drops `connect.{{ domainname_infra }}` from the `dns_records` filter output.

- [x] **Step 5: Cut over from randolph** — randolph's Connect torn down first, then camina's deployed (`6ac888d2`). Randolph's Traefik is left running with no consumer, which ends the #270 pilot in practice; its removal is still an open decision.
  Two Connect servers cannot share one credentials file. Bring randolph's down **first**, then deploy the new one and let it sync before migrating any secret.
  `inventory/host_vars/raspberry-pi4-4gb-randolph/core.yaml` — remove `1password-connect` from `compositions:`, and `reverseproxy` too once confirmed unused. Its host_vars records that 1password-connect is Traefik's only consumer there, so this ends the `#270` internal-wildcard-cert pilot. Confirm that pilot has served its purpose first.

- [x] **Step 6: Move automation off malcolm** — role removed from malcolm's playbook and the launchd daemon uninstalled (`20da7879`), then `automation-infra` deleted entirely (`7658f07c`).
  `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml` — remove `automation-infra`. malcolm keeps ollama and the Apple services.

- [x] **Step 7: Establish the break-glass fallback** — already true and in daily use: malcolm has the checkout (`~/Code/awfulwoman/infra`), the vault password (`~/ansible/.vaultpassword`) and the collections, and every deploy in this migration ran from it. Nothing keeps it current automatically, since malcolm has no scheduled run.
  A controller cannot provision itself from scratch. Keep a working repo checkout, the vault password file, and installed collections on malcolm, so the new box can be rebuilt on the day it is the thing that is broken.

- [x] **Step 8: Verify** — camina deploys the fleet: real runs of `core` from camina against itself, storage, homebrain, agatha, public01 and bertha all pass, plus the reverseproxy composition on every Traefik host. Connect answers on camina and survived a reboot (5+ days uptime since).

  The loopback checks are deferred with step 4. The `--check` run in the original plan is not usable: many read-only `command` tasks are skipped in check mode, so the facts parsed from them are missing and the play fails (`035b7d2e` fixes one such case, in `bootstrap-ubuntu-server`).

**Keep the box dedicated.** homebrain is the cautionary tale — 13 containers, 4.5GB of 7.6GB used, disk at 90%. Controller plus Connect, and nothing else.

---

## Task 3: Foundation — the lookup plugin

No secrets move in this task. The goal is a proven plugin.

- [ ] **Step 1: Write the pure client**
  `plugins/lookup/op_connect_client.py` — `urllib` only, matching `op-infra-write.py`. Resolves item-by-title then field-by-label. No Ansible imports, so pytest can import it directly (`pytest.ini` already puts `plugins/lookup` on `pythonpath`).

  **Look up by title, not UUID.** The current convention hardcodes item UUIDs in role defaults (`composition_gateway_github_item_id: 5edooob5a7kzxkuv5ttu5vdexu`), and `composition-finances/README.md:56-59` records the resulting trap: 1Password reassigns an item's UUID when it moves between vaults. Use `GET /v1/vaults/{vault}/items?filter=title eq "<title>"` to resolve, then `GET /v1/vaults/{vault}/items/{id}` for fields.

  **Assert exactly one match.** 1Password does not enforce unique titles. If the title filter returns more than one item, raise — never pick the first.

  **Guard field selection.** Filter `label is defined` before matching — unlabelled fields (notes) otherwise raise. The existing consumers already get this right (`composition-gateway/tasks/main.yaml:36-40`). Fall back to matching the field `id` when no label matches: Login and API Credential built-ins are addressed by `id` (`username`, `password`, `credential`).

  **Labels must be unique within an item.** Sections do not namespace labels, so the plugin cannot tell two same-labelled fields apart. Either use no sections, or accept the constraint.

  **Cache per run.** Memoise on `(vault, title)`. `vault_password` has 22 references and `vault_server_username` 32; without caching each render is a separate HTTP call.

  **Raise, never return empty.** Any failure must raise with the item title and vault name.

- [ ] **Step 2: Write the Ansible shim**
  `plugins/lookup/onepassword_connect.py` — `LookupModule(LookupBase)` with the `DOCUMENTATION` r-string, following `composition_dns_subdomains.py`. Needs the `sys.path.insert` sibling-import workaround (see that file, lines 22-27). Registered automatically via `ansible.cfg:5`, so it is called by bare name.
  Signature: `lookup('onepassword_connect', <item_title>, <field_label>, vault=<vault_id>)`, `vault` defaulting to Infra. With one vault, `vault=` is never passed in practice — it exists so a second vault can be addressed later without a signature change.

- [ ] **Step 3: Write tests**
  `tests/test_op_connect_client.py` — stub the HTTP layer. Cover: field found, item missing, field missing, duplicate titles returned, unlabelled fields present, field matched by `id` when no label matches, title containing `/`, cache hit.

- [ ] **Step 4: Point the coordinates at loopback and the environment**
  `inventory/group_vars/infra/core.yaml:39-52`:
  ```yaml
  onepassword_connect_host: "http://127.0.0.1:8080"   # loopback on the controller
  onepassword_connect_vault_infra: tsnrmqmuafgj2b5ajwykn7jwpi
  onepassword_connect_token: "{{ lookup('ansible.builtin.env', 'OP_CONNECT_TOKEN') }}"
  ```
  Keep the existing `onepassword_connect_vault_id` as an alias until the two bespoke consumers are collapsed in Task 5, Step 3.
  Plain HTTP is correct — traffic never leaves the loopback interface, and TLS would only add a cert to expire. Keep the host a variable so it can be repointed if a second controller ever appears.

- [ ] **Step 5: Deliver the tokens out of band**
  `OP_CONNECT_TOKEN` (read) and `OP_CONNECT_TOKEN_WRITE` (write). `environment_config` at `core.yaml:102-111` is the established place for env vars, but **the tokens must not go there** — that dict is committed. Document a manual per-controller step, as the vault password file is handled today.

- [ ] **Step 6: Add the collection**
  `meta/requirements.yaml` — add `onepassword.connect`.

- [ ] **Step 7: Add the pre-flight check**
  `roles/preflight-onepassword/` — assert `OP_CONNECT_TOKEN` is set, then `uri` GET `{{ onepassword_connect_host }}/health` with a short timeout, `delegate_to: localhost`, `run_once: true`. Add it early in each host `core.yaml`, next to the `monitoring-healthchecksio` start role.

- [ ] **Step 8: Add the generation playbook**
  `playbooks/utility/provision-secrets.yaml` — the single declarative place secrets get created:
  ```yaml
  - name: Ensure paperless-ngx secrets exist
    onepassword.connect.generic_item:
      hostname: "{{ onepassword_connect_host }}"
      token: "{{ lookup('ansible.builtin.env', 'OP_CONNECT_TOKEN_WRITE') }}"
      vault_id: "{{ onepassword_connect_vault_infra }}"
      title: group/infra/composition-paperless-ngx
      state: present
      tags: [ansible, "group:infra", "role:composition-paperless-ngx"]
      fields:
        - label: paperless_ngx_db_password
          field_type: concealed
          generate_value: on_create      # only when absent — idempotent
          generator_recipe:
            length: 32
            include_letters: true
            include_digits: true
            include_symbols: false
    delegate_to: localhost
    no_log: true
  ```

- [ ] **Step 9: Retire the write script**
  Delete `scripts/op-infra-write.py` and its entry at `scripts/README.md:37`.

- [ ] **Step 10: Fix the contradictory docs**
  `docs/1password-connect.md:66-84` recommends the `community.general.onepassword` lookup, which **contradicts** `core.yaml:46-49` — that lookup shells out to the `op` CLI, which is not installed on the controller. Replace with the new plugin's usage, and update the host/URL for the move off randolph.

- [ ] **Step 11: Add the orphan audit**
  `playbooks/utility/audit-secrets.yaml` — the check that the mechanical naming scheme exists to make possible. Walk every `onepassword_*.yaml` mapping file and assert:
  - every `vault_*` variable resolves to exactly one item and field (`| length > 0`, never the value);
  - every field on every `ansible`-tagged item in Infra has a consumer in the repo;
  - every item title matches the path derived from its mapping file's location.

  Report titles and field labels only. Never print a value.

- [ ] **Step 12: Rename the two pre-existing items**
  `op://Infra/Github` → `group/infra/github`, and the Enable Banking item → `group/infra/composition-finances`. A rename keeps the item UUID — only a move between vaults reassigns it — so the hardcoded IDs at `composition-gateway/defaults/main.yaml:86` and `composition-finances/defaults/main.yaml:18` keep working until Task 5, Step 3 replaces them with title lookups.

- [ ] **Step 13: Verify**
  ```bash
  pytest tests/test_op_connect_client.py

  # resolve a known-good existing item, touching no host
  ansible -m debug -a "msg={{ lookup('onepassword_connect', 'group/infra/github', 'github_token_share_site') | length }}" \
    localhost -e @inventory/group_vars/infra/core.yaml

  # failure modes — all must fail loudly, never return empty
  OP_CONNECT_TOKEN= ansible-playbook ...          # unset token
  # wrong item title; wrong field label; Connect stopped
  ```

---

## Task 4: Migrate infra API tokens

~20 variables, lowest blast radius, each verifiable against a live API. This is the confidence-builder.

Scope: Hetzner, 6× DigitalOcean, Tailscale OAuth, 3× GitHub, healthchecks.io, HuggingFace, Ubuntu Pro.

- [ ] **Step 1: Create the items in 1Password (Infra vault)**
  These are existing live tokens, so **copy** them rather than generating new ones. Titles `group/infra/hetzner`, `group/infra/digitalocean`, `group/infra/tailscale`, `group/infra/github`, `group/infra/healthchecksio`, `group/infra/huggingface`, `group/infra/ubuntu`. Category: API Credential.

- [ ] **Step 2: Add the mappings**
  One plaintext `inventory/group_vars/infra/onepassword_<subject>.yaml` per item, replacing the matching `vault_<subject>.yaml`.

- [ ] **Step 3: Empty the corresponding vault files**
  `vault_hetzner.yaml`, `vault_digitalocean.yaml`, `vault_tailscale.yaml`, `vault_github.yaml`, `vault_healthchecksio.yaml`, `vault_huggingface.yaml`, `vault_ubuntu.yaml`.

- [ ] **Step 4: Verify per the standard per-phase checks** (see Verification below)

---

## Task 5: Migrate app and database secrets

~50 variables — the bulk. Migrate per composition so each is one deploy plus one healthcheck.

**Copy, do not regenerate.** This is the trap in this phase. `generic_item` generation is for *new* secrets. For existing ones:

- **Destructive to rotate:** `vault_n8n_encryption_key` (rotating makes stored n8n credentials permanently undecryptable), `vault_karakeep_meili`, `vault_paperless_ngx_secret_key`. These must be copied, never regenerated.
- **Needs a coordinated change:** every DB password. Writing a new value into `.environment_vars` does not change what Postgres has stored — rotating requires updating the database too, per service.

- [ ] **Step 1: Per composition — create items, copying existing values**
- [ ] **Step 2: Per composition — add mappings, empty the vault file, deploy, healthcheck**
- [ ] **Step 3: Collapse the two bespoke consumers**
  `roles/composition-gateway/tasks/main.yaml:20-43` and `roles/composition-finances/tasks/main.yaml:28-52` — replace the `uri` + `set_fact` pairs with lookups now the plugin is proven.

---

## Task 6: Migrate keys and blobs

Handle carefully — a wrong ZFS passphrase locks a pool.

Scope: `vault_zfsbackups_privatekey_b64` (~125 lines), `vault_zfsbackups_public_key`, `vault_mullvad_wireguard_private_key`, `vault_sitedeployer_*`, `vault_zfs_passphrase` (3 hosts).

- [ ] **Step 1: Migrate one host's `vault_zfs_passphrase` and verify pool decryption before touching the others**
- [ ] **Step 2: Migrate the remaining keys, verifying each consumer**

---

## Task 7: Migrate human-facing credentials

Scope: `vault_password` (9 hosts), WiFi, mail account, Libro.fm, Obsidian, and app admin logins (uptime-kuma, grafana, paperless, pinepods, pihole, qbittorrent, jarvis-editor, peekaping).

These go in Infra like everything else, as Login-category items with the `url` field set so 1Password autofills them in a browser. Per-host logins are `host/<hostname>` with the built-in `username` and `password` fields; app logins are `group/infra/composition-<app>`.

**`vault_password` is the riskiest single item in the plan.** It is the sudo password *and* the macOS login-keychain password across 9 hosts. A bad lookup loses `become` everywhere simultaneously, including the access needed to fix it.

- [ ] **Step 1: Migrate one host's `vault_password`; verify `become` works**
- [ ] **Step 2: Verify the keychain-dependent Apple servers on malcolm** (`system-apple-{reminders,calendar,contacts}-server`)
- [ ] **Step 3: Migrate the remaining 8 hosts**
- [ ] **Step 4: Migrate the remaining human-facing logins**

---

## Task 8: Consolidate what remains

- [ ] **Step 1: Confirm the residual vault surface**
  One residual encrypted file plus the privacy-screen variables (see Edge cases).

- [ ] **Step 2: Rekey the legacy 1.1 blocks**
  45 ciphertext blocks across 17 files still use the identity-less `$ANSIBLE_VAULT;1.1;AES256` header while `ansible.cfg:9` declares `vault_identity = beanpod`. Re-encrypt whatever survives to `1.2;AES256;beanpod` via `playbooks/utility/rekey-ansible-vault.yaml`.

- [ ] **Step 3: Update `plugins/README.md`** — it currently documents only filters.

---

## Files

**New**
- `plugins/lookup/op_connect_client.py`, `plugins/lookup/onepassword_connect.py`
- `tests/test_op_connect_client.py`
- `roles/preflight-onepassword/{tasks,defaults}/main.yaml` + `README.md`
- `playbooks/utility/provision-secrets.yaml`, `playbooks/utility/audit-secrets.yaml`
- `inventory/group_vars/infra/onepassword_<subject>.yaml` — one per item, replacing each `vault_<subject>.yaml`
- `inventory/host_vars/<host>/onepassword_<subject>.yaml` — likewise for host-scoped items
- `inventory/host_vars/minipc-8gb-<name>/{core,vault_credentials}.yaml`
- `playbooks/hosts/minipc-8gb-<name>/core.yaml`

**Modified**
- `inventory/hosts.yaml`
- `inventory/group_vars/infra/core.yaml:39-52`
- `meta/requirements.yaml`
- `plugins/README.md`
- `docs/1password-connect.md`
- `roles/composition-1password-connect/{defaults,tasks,templates}/`
- `inventory/host_vars/raspberry-pi4-4gb-randolph/core.yaml`
- `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`
- `roles/composition-gateway/tasks/main.yaml`, `roles/composition-finances/tasks/main.yaml`
- `roles/ansible-pull/tasks/main.yaml`, `scripts/ansible-pull/bootstrap-ansible-ubuntu-server.sh`
- Per-task: the vault files, emptied as their contents migrate

**Deleted**
- `scripts/op-infra-write.py` and its `scripts/README.md:37` entry

---

## Verification

**Per migration task**

1. `ansible-playbook <host core.yaml> --check --diff --tags <role>` — confirm **no diff** against the pre-migration render. A clean check run is the strongest signal the value resolved identically.
2. Deploy for real, then confirm the service is healthy (`docker ps` healthcheck state, or the app's own endpoint).
3. `git grep '$ANSIBLE_VAULT'` — the count must fall by the expected number.
4. Confirm no plaintext leaked into a rendered file: `ssh <host> 'ls -l <composition_config>/.environment_vars'` should be `0600`, with the value present.

**Generation — proving the agent never sees the secret**

```bash
ansible-playbook playbooks/utility/provision-secrets.yaml --tags <service>
# stdout must show 'changed' with no value. Then confirm it exists:
ansible -m debug -a "msg={{ lookup('onepassword_connect', '<title>', '<field>') | length }}" localhost
```

Asserting on `| length` proves the secret resolved without printing it. Re-running must report `ok`, not `changed` — that is `generate_value: on_create` behaving idempotently.

**Rollback.** Each migration is one commit replacing one `vault_<subject>.yaml` with one `onepassword_<subject>.yaml`. `git revert` restores the ciphertext, which still decrypts with the unchanged vault password. Do not delete a vault file's contents until the task is verified in production.

---

## Edge cases

**What deliberately stays in Ansible Vault.** One residual encrypted file, `inventory/group_vars/infra/vault_onepassword_connect.yaml`, plus the privacy-screen variables:

- `vault_onepassword_connect_credentials` — the credentials JSON the Connect server needs to boot. Cannot live in Connect (the bootstrap paradox, documented at `docs/1password-connect.md:86-89`).
- Domain names (`vault_domainname_*`), `vault_mailprovider_domain` (40 refs), `vault_wifey_name`, disk serials, `vault_server_username`. These grant no access — they are privacy screens, not credentials. Fetching them from Connect would add latency and a runtime dependency for no security gain.

**The residual vault means two systems forever.** There is no end state with a single source of truth. The rule is: Connect holds anything that grants access; the vault holds the bootstrap credential and the privacy screens.

**A new custom plugin sits on the critical path of every secret resolution.** Vault decryption is Ansible core and battle-tested; this replaces it with ~150 lines of repo-local Python. Test it properly (Task 3, Step 3) and make its failures loud.

**Fresh-controller bootstrap gains steps, not loses them.** The new controller needs the vault password file (still, for residuals), plus two env vars, plus a running local Connect.

**`vault_domainname_ew` is load-bearing.** It was previously interpolated into `onepassword_connect_host`. After Task 2 the host is a literal loopback URL, which removes that circular dependency — do not reintroduce it.

---

## Open items

- ~~**A name for the new host**~~ — `minipc-8gb-camina`, at `192.168.1.23` / `100.80.1.23`.
- ~~**Private vault token scope**~~ — dropped. One vault (see design decisions), so there is no second token to scope.
- **Whether the `#270` wildcard-cert pilot on randolph has served its purpose** — decommissioning its reverseproxy ends it.
