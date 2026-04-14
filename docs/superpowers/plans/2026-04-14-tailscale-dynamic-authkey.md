# Tailscale Dynamic Auth Key Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static `vault_tailscale_authkey` with OAuth-based one-time auth key generation at playbook run time, so no long-lived auth key is stored in Ansible Vault.

**Architecture:** A new `network-tailscale-authkey` role exchanges OAuth client credentials (already in vault) for a Bearer token, then calls the Tailscale API to generate a short-lived, one-time-use auth key, setting it as `tailscale_authkey` fact. Existing consumers (`artis3n.tailscale.machine` and the PiKVM role) pick up the fact transparently.

**Tech Stack:** Ansible `uri` module, Tailscale REST API (`/api/v2/oauth/token`, `/api/v2/tailnet/-/keys`), Ansible Vault

---

## Prerequisites

Before running any playbook with this change:

1. Tailscale OAuth client must have `devices:create` scope — verify in Tailscale Admin Console → Settings → OAuth clients.
2. At least one ACL tag (e.g. `tag:server`) must exist in your Tailscale ACL policy. Auth keys generated via OAuth **require** a tag.
3. The OAuth client must be permitted to tag devices with your chosen tag(s).

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| **Create** | `roles/network-tailscale-authkey/tasks/main.yaml` | Exchange OAuth creds → Bearer token → generate one-time auth key → set `tailscale_authkey` fact |
| **Create** | `roles/network-tailscale-authkey/meta/main.yaml` | Role metadata |
| **Modify** | `inventory/group_vars/infra/core.yaml` | Add OAuth var mappings from vault; add `tailscale_node_tags`; remove static `tailscale_authkey` |
| **Modify** | `roles/bootstrap-ubuntu-server/tasks/main.yaml` | Include `network-tailscale-authkey` before tailscale tasks |
| **Modify** | `roles/system-pikvm/tasks/main.yaml` | Check if already connected; include `network-tailscale-authkey` conditionally before `tailscale up` |

---

## Task 1: Create `network-tailscale-authkey` role

**Files:**
- Create: `roles/network-tailscale-authkey/meta/main.yaml`
- Create: `roles/network-tailscale-authkey/tasks/main.yaml`

- [ ] **Step 1.1: Create role meta file**

```yaml
# roles/network-tailscale-authkey/meta/main.yaml
galaxy_info:
  role_name: network-tailscale-authkey
  description: Generates a one-time Tailscale auth key via OAuth and sets it as tailscale_authkey fact
  min_ansible_version: "2.14"
dependencies: []
```

- [ ] **Step 1.2: Create role tasks file**

```yaml
# roles/network-tailscale-authkey/tasks/main.yaml
# code: language=ansible

- name: Exchange OAuth credentials for Bearer token
  ansible.builtin.uri:
    url: https://api.tailscale.com/api/v2/oauth/token
    method: POST
    body_format: form-urlencoded
    body:
      grant_type: client_credentials
      client_id: "{{ tailscale_oauth_client_id }}"
      client_secret: "{{ tailscale_oauth_client_secret }}"
    status_code: 200
  register: tailscale_oauth_token_response
  no_log: true

- name: Generate one-time Tailscale auth key
  ansible.builtin.uri:
    url: https://api.tailscale.com/api/v2/tailnet/-/keys
    method: POST
    headers:
      Authorization: "Bearer {{ tailscale_oauth_token_response.json.access_token }}"
    body_format: json
    body:
      capabilities:
        devices:
          create:
            reusable: false
            ephemeral: false
            preauthorized: true
            tags: "{{ tailscale_node_tags }}"
      expirySeconds: 300
    status_code: 200
  register: tailscale_key_response
  no_log: true

- name: Set tailscale_authkey fact
  ansible.builtin.set_fact:
    tailscale_authkey: "{{ tailscale_key_response.json.key }}"
  no_log: true
```

- [ ] **Step 1.3: Commit**

```bash
git add roles/network-tailscale-authkey/
git commit -m "feat(network-tailscale-authkey): add role to generate one-time auth key via OAuth"
```

---

## Task 2: Update `group_vars/infra/core.yaml`

**Files:**
- Modify: `inventory/group_vars/infra/core.yaml`

- [ ] **Step 2.1: Replace static authkey with OAuth vars**

Remove this line from `inventory/group_vars/infra/core.yaml`:
```yaml
tailscale_authkey: "{{ vault_tailscale_authkey }}"
```

Add these lines in its place:
```yaml
tailscale_oauth_client_id: "{{ vault_tailscale_authkey_rotation_app_client_id }}"
tailscale_oauth_client_secret: "{{ vault_tailscale_authkey_rotation_app_client_secret }}"
tailscale_node_tags:
  - tag:auto-generated
```

- [ ] **Step 2.2: Commit**

```bash
git add inventory/group_vars/infra/core.yaml
git commit -m "feat(inventory): replace static tailscale authkey with OAuth credential vars"
```

---

## Task 3: Update `bootstrap-ubuntu-server` to generate key before enrollment

**Files:**
- Modify: `roles/bootstrap-ubuntu-server/tasks/main.yaml`

The current tailscale block (lines 163–173) looks like:

```yaml
- name: Tailscale
  ansible.builtin.include_role:
    name: artis3n.tailscale.machine
  when: tailscale_exit_node is undefined or tailscale_exit_node is not true

- name: Tailscale - with exit node
  ansible.builtin.include_role:
    name: artis3n.tailscale.machine
  vars:
    tailscale_args: "--advertise-exit-node"
  when: tailscale_exit_node is defined and tailscale_exit_node is true
```

- [ ] **Step 3.1: Insert key generation task before the tailscale block**

Insert the following immediately before the existing `Tailscale` task:

```yaml
- name: Generate Tailscale auth key
  ansible.builtin.include_role:
    name: network-tailscale-authkey
```

The block should now read:

```yaml
- name: Generate Tailscale auth key
  ansible.builtin.include_role:
    name: network-tailscale-authkey

- name: Tailscale
  ansible.builtin.include_role:
    name: artis3n.tailscale.machine
  when: tailscale_exit_node is undefined or tailscale_exit_node is not true

- name: Tailscale - with exit node
  ansible.builtin.include_role:
    name: artis3n.tailscale.machine
  vars:
    tailscale_args: "--advertise-exit-node"
  when: tailscale_exit_node is defined and tailscale_exit_node is true
```

- [ ] **Step 3.2: Commit**

```bash
git add roles/bootstrap-ubuntu-server/tasks/main.yaml
git commit -m "feat(bootstrap-ubuntu-server): generate dynamic tailscale auth key before enrollment"
```

---

## Task 4: Update `system-pikvm` to generate key conditionally

**Files:**
- Modify: `roles/system-pikvm/tasks/main.yaml`

The PiKVM role uses `tailscale up --auth-key=` directly (lines 59–67) without checking if the device is already connected. We must gate key generation and `tailscale up` on connection state to avoid consuming a one-time key on an already-enrolled device.

- [ ] **Step 4.1: Add status check and conditional key generation before `tailscale up`**

Replace the existing tailscale block:

```yaml
- name: Ensure the Tailnet is brought up
  ansible.builtin.command:
    cmd: "tailscale up --auth-key={{ tailscale_authkey }}"
  register: tailscaleup_result
  changed_when: tailscaleup_result.rc != 0

- name: DEBUG Tailnet output due to errors
  ansible.builtin.debug:
    var: tailscaleup_result
  when: tailscaleup_result.rc != 0
```

With:

```yaml
- name: Check if Tailscale is already connected
  ansible.builtin.command:
    cmd: tailscale status
  register: tailscale_status
  changed_when: false
  failed_when: false

- name: Generate Tailscale auth key
  ansible.builtin.include_role:
    name: network-tailscale-authkey
  when: tailscale_status.rc != 0

- name: Ensure the Tailnet is brought up
  ansible.builtin.command:
    cmd: "tailscale up --auth-key={{ tailscale_authkey }}"
  register: tailscaleup_result
  changed_when: tailscaleup_result.rc == 0
  when: tailscale_status.rc != 0

- name: DEBUG Tailnet output due to errors
  ansible.builtin.debug:
    var: tailscaleup_result
  when: tailscale_status.rc != 0 and tailscaleup_result.rc != 0
```

- [ ] **Step 4.2: Commit**

```bash
git add roles/system-pikvm/tasks/main.yaml
git commit -m "feat(system-pikvm): generate dynamic tailscale auth key with idempotency check"
```

---

## Task 5: Deprecate the static vault auth key

**Files:**
- Modify: `inventory/group_vars/infra/vault_tailscale.yaml`

Once you have verified the new flow works against at least one host, remove the old static key from vault.

- [ ] **Step 5.1: Decrypt and edit the vault file**

```bash
ansible-vault edit inventory/group_vars/infra/vault_tailscale.yaml
```

Remove the `vault_tailscale_authkey` block entirely:

```yaml
# Remove this:
vault_tailscale_authkey: !vault |
          $ANSIBLE_VAULT;1.2;AES256;beanpod
          ...
```

- [ ] **Step 5.2: Commit**

```bash
git add inventory/group_vars/infra/vault_tailscale.yaml
git commit -m "chore(vault): remove deprecated static tailscale auth key"
```

---

## Verification

After implementing all tasks, verify end-to-end on one non-critical host before running across all infra:

```bash
# Dry run against a single host to check variable resolution
ansible-playbook playbooks/baremetal/core.yaml --limit host-belinda --check -v

# Live run against one host (will actually enroll/re-enroll via fresh key)
ansible-playbook playbooks/baremetal/core.yaml --limit host-belinda
```

Expected: `tailscale status` on the target host shows it connected to the tailnet after the run. Tailscale Admin Console → Machines should show a new auth event with a timestamp matching the run.
