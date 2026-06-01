# system-mcp-gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an Ansible role that clones, configures, and runs the `awfulwoman/gateway` MCP server as a launchd service on malcolm (macOS 15).

**Architecture:** Self-contained role — clones the repo to `/opt/awfulwoman/gateway`, installs Python deps via `uv sync`, deploys a `.env` credential file, a launchd plist, and grants TCC permissions for Calendar/Reminders/Contacts. No dependency on `system-repos`.

**Tech Stack:** Ansible, community.general.homebrew, ansible.builtin.git, Jinja2 templates, launchd, macOS TCC sqlite3

---

### Task 1: Role skeleton and defaults

**Files:**
- Create: `roles/system-mcp-gateway/defaults/main.yaml`
- Create: `roles/system-mcp-gateway/tasks/main.yaml`
- Create: `roles/system-mcp-gateway/tasks/install-macos.yaml` (empty placeholder)

- [ ] **Step 1: Create `defaults/main.yaml`**

```yaml
---
system_mcp_gateway_base_dir: /opt/awfulwoman
system_mcp_gateway_repo_dir: "{{ system_mcp_gateway_base_dir }}/gateway"
system_mcp_gateway_repo_url: "https://github.com/awfulwoman/gateway.git"
system_mcp_gateway_repo_version: main

system_mcp_gateway_imap_host: "imap.mailbox.org"
system_mcp_gateway_imap_port: 993
system_mcp_gateway_imap_username: ""
system_mcp_gateway_imap_password: ""

system_mcp_gateway_obsidian_vault_path: ""

system_mcp_gateway_karakeep_base_url: ""
system_mcp_gateway_karakeep_api_key: ""

system_mcp_gateway_server_host: "127.0.0.1"
system_mcp_gateway_server_port: 4000
```

- [ ] **Step 2: Create `tasks/main.yaml`**

```yaml
---
- name: Install gateway MCP server (macOS)
  ansible.builtin.include_tasks: install-macos.yaml
  when: ansible_facts['os_family'] == 'Darwin'
```

- [ ] **Step 3: Create empty `tasks/install-macos.yaml`**

```yaml
---
```

- [ ] **Step 4: Commit**

```bash
git add roles/system-mcp-gateway/
git commit -m "feat(system-mcp-gateway): role skeleton and defaults"
```

---

### Task 2: Install uv, base dir, and git clone

**Files:**
- Modify: `roles/system-mcp-gateway/tasks/install-macos.yaml`

- [ ] **Step 1: Add tasks to `install-macos.yaml`**

Replace the empty file with:

```yaml
---
- name: Ensure uv is installed via Homebrew
  community.general.homebrew:
    name: uv
    state: present

- name: Ensure /opt/awfulwoman base directory exists
  become: true
  ansible.builtin.file:
    path: "{{ system_mcp_gateway_base_dir }}"
    state: directory
    mode: "0755"
    owner: "{{ ansible_user }}"
    group: staff

- name: Ensure gateway repo is cloned/updated
  ansible.builtin.git:
    repo: "{{ system_mcp_gateway_repo_url }}"
    dest: "{{ system_mcp_gateway_repo_dir }}"
    version: "{{ system_mcp_gateway_repo_version }}"
    update: true

- name: Ensure Python dependencies are installed
  ansible.builtin.command:
    cmd: uv sync
    chdir: "{{ system_mcp_gateway_repo_dir }}"
  changed_when: false
```

- [ ] **Step 2: Verify syntax**

```bash
ansible-playbook --syntax-check playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml
```

Expected: `playbook: playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml` with no errors. (The role isn't wired in yet — this just confirms no parse errors in the role files.)

- [ ] **Step 3: Commit**

```bash
git add roles/system-mcp-gateway/tasks/install-macos.yaml
git commit -m "feat(system-mcp-gateway): install uv, clone repo, uv sync"
```

---

### Task 3: `.env` template

**Files:**
- Create: `roles/system-mcp-gateway/templates/env.j2`

- [ ] **Step 1: Create `templates/env.j2`**

```jinja
# Managed by Ansible - do not edit manually
# roles/system-mcp-gateway

GATEWAY_IMAP__HOST={{ system_mcp_gateway_imap_host }}
GATEWAY_IMAP__PORT={{ system_mcp_gateway_imap_port }}
GATEWAY_IMAP__USERNAME={{ system_mcp_gateway_imap_username }}
GATEWAY_IMAP__PASSWORD={{ system_mcp_gateway_imap_password }}

GATEWAY_OBSIDIAN__VAULT_PATH={{ system_mcp_gateway_obsidian_vault_path }}

GATEWAY_KARAKEEP__BASE_URL={{ system_mcp_gateway_karakeep_base_url }}
GATEWAY_KARAKEEP__API_KEY={{ system_mcp_gateway_karakeep_api_key }}

GATEWAY_SERVER__HOST={{ system_mcp_gateway_server_host }}
GATEWAY_SERVER__PORT={{ system_mcp_gateway_server_port }}
```

- [ ] **Step 2: Add deploy task to `install-macos.yaml`** (append after the `uv sync` task)

```yaml
- name: Ensure logs directory exists
  ansible.builtin.file:
    path: "{{ system_mcp_gateway_repo_dir }}/logs"
    state: directory
    mode: "0755"

- name: Deploy .env configuration
  ansible.builtin.template:
    src: env.j2
    dest: "{{ system_mcp_gateway_repo_dir }}/.env"
    mode: "0600"
```

- [ ] **Step 3: Commit**

```bash
git add roles/system-mcp-gateway/templates/env.j2 roles/system-mcp-gateway/tasks/install-macos.yaml
git commit -m "feat(system-mcp-gateway): deploy .env and logs directory"
```

---

### Task 4: launchd plist and service management

**Files:**
- Create: `roles/system-mcp-gateway/templates/launchd.plist.j2`
- Modify: `roles/system-mcp-gateway/tasks/install-macos.yaml`

- [ ] **Step 1: Create `templates/launchd.plist.j2`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.awfulwoman.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/uv</string>
        <string>run</string>
        <string>gateway</string>
        <string>--transport</string>
        <string>http</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{{ system_mcp_gateway_repo_dir }}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{{ system_mcp_gateway_repo_dir }}/logs/gateway.log</string>
    <key>StandardErrorPath</key>
    <string>{{ system_mcp_gateway_repo_dir }}/logs/gateway.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 2: Append service tasks to `install-macos.yaml`**

```yaml
- name: Ensure LaunchAgents directory exists
  ansible.builtin.file:
    path: "{{ ansible_facts.user_dir }}/Library/LaunchAgents"
    state: directory
    mode: "0755"

- name: Deploy launchd plist
  ansible.builtin.template:
    src: launchd.plist.j2
    dest: "{{ ansible_facts.user_dir }}/Library/LaunchAgents/com.awfulwoman.gateway.plist"
    mode: "0644"
  register: gateway_plist

- name: Unload service before reload on plist change # noqa: no-handler
  ansible.builtin.command: "launchctl unload {{ ansible_facts.user_dir }}/Library/LaunchAgents/com.awfulwoman.gateway.plist"
  when: gateway_plist.changed
  changed_when: false
  failed_when: false

- name: Load service # noqa: no-handler
  ansible.builtin.command: "launchctl load {{ ansible_facts.user_dir }}/Library/LaunchAgents/com.awfulwoman.gateway.plist"
  when: gateway_plist.changed
  register: gateway_load
  changed_when: gateway_load.rc == 0
  failed_when: false

- name: Ensure service is running
  ansible.builtin.command: launchctl list com.awfulwoman.gateway
  register: gateway_status
  changed_when: false
  failed_when: gateway_status.rc != 0
```

- [ ] **Step 3: Commit**

```bash
git add roles/system-mcp-gateway/templates/launchd.plist.j2 roles/system-mcp-gateway/tasks/install-macos.yaml
git commit -m "feat(system-mcp-gateway): launchd plist and service management"
```

---

### Task 5: TCC permissions (macOS 15 only)

**Files:**
- Modify: `roles/system-mcp-gateway/tasks/install-macos.yaml`

The TCC database at `~/Library/Application Support/com.apple.TCC/TCC.db` controls which apps can access Calendar, Reminders, and Contacts. The gateway runs via `uv`, so both `org.python.python` (bundle type 0) and the real uv binary path (bundle type 1, resolved past Homebrew symlinks) need entries. This only applies to the macOS 15 TCC schema — a version guard prevents silent failures on future macOS versions.

- [ ] **Step 1: Append TCC tasks to `install-macos.yaml`**

```yaml
- name: Check macOS version for TCC compatibility
  ansible.builtin.debug:
    msg: "WARNING: TCC permission grant skipped - only supported on macOS 15.x. Grant Calendar/Reminders/Contacts access manually for the gateway process."
  when: not (ansible_facts['distribution_version'] is version('15', '>=') and ansible_facts['distribution_version'] is version('16', '<'))

- name: Find real path to uv binary (macOS 15 only)
  ansible.builtin.command: which uv
  register: uv_which
  changed_when: false
  when: ansible_facts['distribution_version'] is version('15', '>=') and ansible_facts['distribution_version'] is version('16', '<')

- name: Resolve uv symlink to real binary path (macOS 15 only)
  ansible.builtin.command: "python3 -c \"import os; print(os.path.realpath('{{ uv_which.stdout }}'))\""
  register: uv_real
  changed_when: false
  when: ansible_facts['distribution_version'] is version('15', '>=') and ansible_facts['distribution_version'] is version('16', '<')

- name: Grant TCC permissions for Calendar, Reminders, Contacts (macOS 15 only)
  ansible.builtin.command: >
    sqlite3 "{{ ansible_facts.user_dir }}/Library/Application Support/com.apple.TCC/TCC.db"
    "INSERT OR REPLACE INTO access
      (service, client, client_type, auth_value, auth_reason, auth_version, csreq, indirect_object_identifier)
    VALUES
      ('kTCCServiceCalendar', 'org.python.python', 0, 2, 3, 1, NULL, 'UNUSED'),
      ('kTCCServiceCalendar', '{{ uv_real.stdout }}', 1, 2, 3, 1, NULL, 'UNUSED'),
      ('kTCCServiceReminders', 'org.python.python', 0, 2, 3, 1, NULL, 'UNUSED'),
      ('kTCCServiceReminders', '{{ uv_real.stdout }}', 1, 2, 3, 1, NULL, 'UNUSED'),
      ('kTCCServiceAddressBook', 'org.python.python', 0, 2, 3, 1, NULL, 'UNUSED'),
      ('kTCCServiceAddressBook', '{{ uv_real.stdout }}', 1, 2, 3, 1, NULL, 'UNUSED');"
  changed_when: false
  when: ansible_facts['distribution_version'] is version('15', '>=') and ansible_facts['distribution_version'] is version('16', '<')
```

- [ ] **Step 2: Commit**

```bash
git add roles/system-mcp-gateway/tasks/install-macos.yaml
git commit -m "feat(system-mcp-gateway): TCC permissions for Calendar/Reminders/Contacts (macOS 15)"
```

---

### Task 6: README

**Files:**
- Create: `roles/system-mcp-gateway/README.md`

- [ ] **Step 1: Create `roles/system-mcp-gateway/README.md`**

```markdown
# system-mcp-gateway

Installs and runs the [gateway](https://github.com/awfulwoman/gateway) MCP server as a launchd service on macOS. Deploys to `/opt/awfulwoman/gateway`.

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_mcp_gateway_base_dir` | `/opt/awfulwoman` | Base directory for deployed service apps |
| `system_mcp_gateway_repo_dir` | `{{ system_mcp_gateway_base_dir }}/gateway` | Clone destination |
| `system_mcp_gateway_repo_url` | `https://github.com/awfulwoman/gateway.git` | |
| `system_mcp_gateway_repo_version` | `main` | Branch/tag to deploy |
| `system_mcp_gateway_imap_host` | `imap.mailbox.org` | |
| `system_mcp_gateway_imap_port` | `993` | |
| `system_mcp_gateway_imap_username` | `""` | |
| `system_mcp_gateway_imap_password` | `""` | Store in vault |
| `system_mcp_gateway_obsidian_vault_path` | `""` | Absolute path to vault |
| `system_mcp_gateway_karakeep_base_url` | `""` | |
| `system_mcp_gateway_karakeep_api_key` | `""` | Optional |
| `system_mcp_gateway_server_host` | `127.0.0.1` | |
| `system_mcp_gateway_server_port` | `4000` | |

## After deployment

Register the MCP server with Claude Code once:

```bash
claude mcp add --transport http gateway --scope user http://127.0.0.1:4000/mcp
```

## TCC note

Calendar, Reminders, and Contacts access is granted automatically on macOS 15.x. On other versions, grant access manually in System Settings > Privacy & Security.
```

- [ ] **Step 2: Commit**

```bash
git add roles/system-mcp-gateway/README.md
git commit -m "docs(system-mcp-gateway): add README"
```

---

### Task 7: Wire into malcolm's playbook and host_vars

**Files:**
- Modify: `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`
- Modify: `inventory/host_vars/apple-macmini-m4-16gb-malcolm/core.yaml`

- [ ] **Step 1: Add role to malcolm's `core.yaml` playbook**

In `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`, add after the `system-obsidian-headless` role entry (before the final healthchecksio ping):

```yaml
  - role: system-mcp-gateway
    tags: [system, system-mcp-gateway]
```

- [ ] **Step 2: Add variables to malcolm's host_vars**

In `inventory/host_vars/apple-macmini-m4-16gb-malcolm/core.yaml`, add a new section at the end:

```yaml
# -------------------------------------------------------------------
# MCP GATEWAY
# -------------------------------------------------------------------
system_mcp_gateway_imap_username: "{{ vault_mailprovider_user }}"
system_mcp_gateway_imap_password: "{{ vault_mailprovider_password }}"
system_mcp_gateway_obsidian_vault_path: "{{ ansible_facts.user_dir }}/Obsidian"
system_mcp_gateway_karakeep_base_url: "https://karakeep.{{ domainname_infra }}"
```

- [ ] **Step 3: Verify syntax**

```bash
ansible-playbook --syntax-check playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml inventory/host_vars/apple-macmini-m4-16gb-malcolm/core.yaml
git commit -m "feat(malcolm): wire system-mcp-gateway into core playbook"
```

---

### Task 8: Deploy to malcolm

- [ ] **Step 1: Run the role against malcolm with tag filter**

```bash
ansible-playbook playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml --tags system-mcp-gateway
```

Expected: all tasks green or yellow (changed). Final task `Ensure service is running` must pass (rc=0).

- [ ] **Step 2: Verify the service is up on malcolm**

```bash
ssh malcolm "launchctl list com.awfulwoman.gateway"
```

Expected: output includes `com.awfulwoman.gateway` with a PID (not `-`).

- [ ] **Step 3: Check gateway is responding**

```bash
ssh malcolm "curl -s http://127.0.0.1:4000/mcp"
```

Expected: some JSON response (not a connection refused error).

- [ ] **Step 4: Check logs for errors**

```bash
ssh malcolm "tail -20 /opt/awfulwoman/gateway/logs/gateway.err"
```

Expected: no Python tracebacks or credential errors.
