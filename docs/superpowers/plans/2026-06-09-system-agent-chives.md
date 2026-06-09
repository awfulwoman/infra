# system-agent-chives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `system-agent-chives` Ansible role that deploys the chives AI agent as a persistent launchd service on Malcolm.

**Architecture:** The role owns a clean deployment clone at `/opt/awfulwoman/chives`, separate from the dev checkout. It removes the legacy `com.chives.agent` launchd service installed by the repo's own `install_service.sh`, then installs a new `com.awfulwoman.chives` service via launchd plist. Configuration is injected via a templated `.env` file.

**Tech Stack:** Ansible, uv (Python env manager), launchd (macOS service manager), pydantic-settings (`CHIVES_` env prefix), Homebrew.

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Create | `roles/system-agent-chives/defaults/main.yaml` | Default variable values |
| Create | `roles/system-agent-chives/tasks/main.yaml` | macOS OS guard → include |
| Create | `roles/system-agent-chives/tasks/install-macos.yaml` | Full install task list |
| Create | `roles/system-agent-chives/templates/env.j2` | `.env` config for chives |
| Create | `roles/system-agent-chives/templates/launchd.plist.j2` | launchd service plist |
| Create | `roles/system-agent-chives/README.md` | Role documentation |
| Modify | `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml` | Wire in new role |

---

### Task 1: Role skeleton and defaults

**Files:**
- Create: `roles/system-agent-chives/defaults/main.yaml`
- Create: `roles/system-agent-chives/tasks/main.yaml`

- [ ] **Step 1: Create role directory structure**

```bash
mkdir -p roles/system-agent-chives/defaults
mkdir -p roles/system-agent-chives/tasks
mkdir -p roles/system-agent-chives/templates
```

- [ ] **Step 2: Write `defaults/main.yaml`**

```yaml
---
system_agent_chives_base_dir: "{{ awfulwoman_opt_dir }}"
system_agent_chives_repo_dir: "{{ system_agent_chives_base_dir }}/chives"
system_agent_chives_repo_url: "git@github.com:awfulwoman/chives.git"
system_agent_chives_repo_version: main

system_agent_chives_llm_base_url: "http://localhost:11434/v1"
system_agent_chives_llm_model: "gemma4:12b-mlx"
system_agent_chives_llm_api_key: "ollama"

system_agent_chives_telegram_token: "{{ vault_chives_telegram_token }}"
system_agent_chives_telegram_chat_ids: "{{ vault_chives_telegram_chat_ids }}"

system_agent_chives_imap_host: "imap.mailbox.org"
system_agent_chives_imap_port: 993
system_agent_chives_imap_username: "{{ vault_mailprovider_user }}"
system_agent_chives_imap_password: "{{ vault_mailprovider_password }}"

system_agent_chives_morning_brief_time: "08:00"
system_agent_chives_event_reminder_minutes: 15
system_agent_chives_idle_checkin_hours: 0
```

- [ ] **Step 3: Write `tasks/main.yaml`**

```yaml
---
- name: Install chives agent (macOS)
  ansible.builtin.include_tasks: install-macos.yaml
  when: ansible_facts['os_family'] == 'Darwin'
```

- [ ] **Step 4: Commit**

```bash
git add roles/system-agent-chives/
git commit -m "feat: scaffold system-agent-chives role with defaults"
```

---

### Task 2: Install tasks — legacy cleanup through repo setup

**Files:**
- Create: `roles/system-agent-chives/tasks/install-macos.yaml` (first half)

- [ ] **Step 1: Write the opening of `tasks/install-macos.yaml`**

```yaml
---
- name: Unload legacy chives service if running
  ansible.builtin.command: >
    launchctl unload {{ ansible_facts.user_dir }}/Library/LaunchAgents/com.chives.agent.plist
  changed_when: false
  failed_when: false

- name: Remove legacy chives launchd plist
  ansible.builtin.file:
    path: "{{ ansible_facts.user_dir }}/Library/LaunchAgents/com.chives.agent.plist"
    state: absent

- name: Ensure uv is installed via Homebrew
  community.general.homebrew:
    name: uv
    state: present

- name: Ensure /opt/awfulwoman base directory exists
  become: true
  ansible.builtin.file:
    path: "{{ system_agent_chives_base_dir }}"
    state: directory
    mode: "0755"
    owner: "{{ ansible_user }}"
    group: staff

- name: Ensure chives repo is cloned/updated
  ansible.builtin.git:
    repo: "{{ system_agent_chives_repo_url }}"
    dest: "{{ system_agent_chives_repo_dir }}"
    version: "{{ system_agent_chives_repo_version }}"
    update: true
  register: chives_git

- name: Ensure Python dependencies are installed
  ansible.builtin.command:
    cmd: /opt/homebrew/bin/uv sync
    chdir: "{{ system_agent_chives_repo_dir }}"
  changed_when: false

- name: Ensure logs directory exists
  ansible.builtin.file:
    path: "{{ system_agent_chives_repo_dir }}/logs"
    state: directory
    mode: "0755"
```

- [ ] **Step 2: Run pre-commit to verify YAML is well-formed**

```bash
pre-commit run check-yaml --all-files
```

Expected: Passed (or Skipped if no yaml files trigger it — the new file will be checked).

- [ ] **Step 3: Commit**

```bash
git add roles/system-agent-chives/tasks/install-macos.yaml
git commit -m "feat: add legacy cleanup and repo setup tasks to system-agent-chives"
```

---

### Task 3: Templates and service deployment tasks

**Files:**
- Create: `roles/system-agent-chives/templates/env.j2`
- Create: `roles/system-agent-chives/templates/launchd.plist.j2`
- Modify: `roles/system-agent-chives/tasks/install-macos.yaml` (append remaining tasks)

- [ ] **Step 1: Write `templates/env.j2`**

```
# Managed by Ansible - do not edit manually
# roles/system-agent-chives

CHIVES_LLM__BASE_URL={{ system_agent_chives_llm_base_url }}
CHIVES_LLM__MODEL={{ system_agent_chives_llm_model }}
CHIVES_LLM__API_KEY={{ system_agent_chives_llm_api_key }}

CHIVES_TELEGRAM__BOT_TOKEN={{ system_agent_chives_telegram_token }}
CHIVES_TELEGRAM__ALLOWED_CHAT_IDS={{ system_agent_chives_telegram_chat_ids | to_json }}

CHIVES_IMAP__HOST={{ system_agent_chives_imap_host }}
CHIVES_IMAP__PORT={{ system_agent_chives_imap_port }}
CHIVES_IMAP__USERNAME={{ system_agent_chives_imap_username }}
CHIVES_IMAP__PASSWORD={{ system_agent_chives_imap_password }}

CHIVES_MORNING_BRIEF_TIME={{ system_agent_chives_morning_brief_time }}
CHIVES_EVENT_REMINDER_MINUTES={{ system_agent_chives_event_reminder_minutes }}
CHIVES_IDLE_CHECKIN_HOURS={{ system_agent_chives_idle_checkin_hours }}
```

- [ ] **Step 2: Write `templates/launchd.plist.j2`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.awfulwoman.chives</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/uv</string>
        <string>run</string>
        <string>python</string>
        <string>-m</string>
        <string>chives.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{{ system_agent_chives_repo_dir }}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{{ system_agent_chives_repo_dir }}/logs/chives.log</string>
    <key>StandardErrorPath</key>
    <string>{{ system_agent_chives_repo_dir }}/logs/chives.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 3: Append service deployment tasks to `tasks/install-macos.yaml`**

Append the following to the end of the existing file:

```yaml
- name: Ensure LaunchAgents directory exists
  ansible.builtin.file:
    path: "{{ ansible_facts.user_dir }}/Library/LaunchAgents"
    state: directory
    mode: "0755"

- name: Deploy launchd plist
  ansible.builtin.template:
    src: launchd.plist.j2
    dest: "{{ ansible_facts.user_dir }}/Library/LaunchAgents/com.awfulwoman.chives.plist"
    mode: "0644"
  register: chives_plist

- name: Deploy .env configuration
  ansible.builtin.template:
    src: env.j2
    dest: "{{ system_agent_chives_repo_dir }}/.env"
    mode: "0600"
  register: chives_env

- name: Unload service before reload on plist or .env change # noqa: no-handler
  ansible.builtin.command: >
    launchctl unload {{ ansible_facts.user_dir }}/Library/LaunchAgents/com.awfulwoman.chives.plist
  when: chives_plist.changed or chives_env.changed or chives_git.changed
  changed_when: false
  failed_when: false

- name: Load service # noqa: no-handler
  ansible.builtin.command: >
    launchctl load {{ ansible_facts.user_dir }}/Library/LaunchAgents/com.awfulwoman.chives.plist
  when: chives_plist.changed or chives_env.changed or chives_git.changed
  register: chives_load
  changed_when: chives_load.rc == 0
  failed_when: false

- name: Ensure service is running
  ansible.builtin.command: launchctl list com.awfulwoman.chives
  register: chives_status
  changed_when: false
  failed_when: chives_status.rc != 0
```

- [ ] **Step 4: Run pre-commit**

```bash
pre-commit run --all-files
```

Expected: All checks pass.

- [ ] **Step 5: Commit**

```bash
git add roles/system-agent-chives/templates/ roles/system-agent-chives/tasks/install-macos.yaml
git commit -m "feat: add templates and service deployment tasks to system-agent-chives"
```

---

### Task 4: TCC permission tasks

**Files:**
- Modify: `roles/system-agent-chives/tasks/install-macos.yaml` (append TCC tasks)

- [ ] **Step 1: Append TCC tasks to `tasks/install-macos.yaml`**

```yaml
- name: Check macOS version for TCC compatibility
  ansible.builtin.debug:
    msg: >
      WARNING: TCC permission grant skipped - only supported on macOS 15.x.
      Grant Calendar/Reminders/Contacts access manually for the chives process.
  when: ansible_facts['distribution_version'] is version('15', '<')

- name: Resolve uv symlink to real binary path
  ansible.builtin.command: "python3 -c \"import os; print(os.path.realpath('/opt/homebrew/bin/uv'))\""
  register: uv_real
  changed_when: false
  when: ansible_facts['distribution_version'] is version('15', '>=')

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
  when: ansible_facts['distribution_version'] is version('15', '>=')
```

- [ ] **Step 2: Run pre-commit**

```bash
pre-commit run --all-files
```

Expected: All checks pass.

- [ ] **Step 3: Commit**

```bash
git add roles/system-agent-chives/tasks/install-macos.yaml
git commit -m "feat: add TCC permission tasks to system-agent-chives"
```

---

### Task 5: README

**Files:**
- Create: `roles/system-agent-chives/README.md`

- [ ] **Step 1: Write `README.md`**

~~~~markdown
# system-agent-chives

Installs and runs the [chives](https://github.com/awfulwoman/chives) AI agent as a launchd service on macOS. Deploys to `/opt/awfulwoman/chives`.

Chives is a Telegram-connected AI agent with calendar, reminders, contacts, email, memory, and scheduling tools. It also serves an OpenWebUI-compatible API on port 8080.

## Prerequisites

Add the following to the host's vault credentials file before running:

```bash
ansible-vault encrypt_string "$(echo -n 'YOUR_TELEGRAM_BOT_TOKEN')" --name 'vault_chives_telegram_token'
ansible-vault encrypt_string '[123456789]' --name 'vault_chives_telegram_chat_ids'
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_agent_chives_base_dir` | `{{ awfulwoman_opt_dir }}` | Base dir for deployed service apps |
| `system_agent_chives_repo_dir` | `{{ system_agent_chives_base_dir }}/chives` | Clone destination |
| `system_agent_chives_repo_url` | `git@github.com:awfulwoman/chives.git` | |
| `system_agent_chives_repo_version` | `main` | Branch/tag to deploy |
| `system_agent_chives_llm_base_url` | `http://localhost:11434/v1` | Ollama endpoint |
| `system_agent_chives_llm_model` | `gemma4:12b-mlx` | Ollama model name |
| `system_agent_chives_llm_api_key` | `ollama` | |
| `system_agent_chives_telegram_token` | `{{ vault_chives_telegram_token }}` | |
| `system_agent_chives_telegram_chat_ids` | `{{ vault_chives_telegram_chat_ids }}` | JSON list of allowed chat IDs |
| `system_agent_chives_imap_host` | `imap.mailbox.org` | |
| `system_agent_chives_imap_port` | `993` | |
| `system_agent_chives_imap_username` | `{{ vault_mailprovider_user }}` | Shared with system-mcp-gateway |
| `system_agent_chives_imap_password` | `{{ vault_mailprovider_password }}` | Shared with system-mcp-gateway |
| `system_agent_chives_morning_brief_time` | `08:00` | Daily brief schedule (HH:MM) |
| `system_agent_chives_event_reminder_minutes` | `15` | Minutes before events to send reminder |
| `system_agent_chives_idle_checkin_hours` | `0` | Hours of silence before proactive check-in (0 = disabled) |

## TCC note

Calendar, Reminders, and Contacts access is granted automatically on macOS 15.x. On other versions, grant access manually in System Settings > Privacy & Security.

## Legacy service removal

This role automatically removes the `com.chives.agent` launchd service installed by chives's own `scripts/install_service.sh`, if present. No data is migrated from the old install.
~~~~

- [ ] **Step 2: Commit**

```bash
git add roles/system-agent-chives/README.md
git commit -m "docs: add README for system-agent-chives role"
```

---

### Task 6: Vault credentials and playbook wiring

**Files:**
- Modify: `inventory/host_vars/apple-macmini-m4-16gb-malcolm/vault_credentials.yaml`
- Modify: `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`

- [ ] **Step 1: Add vault variables for chives Telegram credentials**

Edit the Malcolm vault file with `ansible-vault edit`:

```bash
ansible-vault edit inventory/host_vars/apple-macmini-m4-16gb-malcolm/vault_credentials.yaml
```

Add the following entries (encrypt each secret using ansible-vault encrypt_string before adding):

```yaml
vault_chives_telegram_token: "YOUR_TELEGRAM_BOT_TOKEN"
vault_chives_telegram_chat_ids:
  - YOUR_CHAT_ID
```

To generate the encrypted values independently first:

```bash
ansible-vault encrypt_string "$(echo -n 'YOUR_TELEGRAM_BOT_TOKEN')" --name 'vault_chives_telegram_token'
```

- [ ] **Step 2: Add `system-agent-chives` role to Malcolm's `core.yaml`**

In `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`, add the new role after `system-mcp-gateway`:

```yaml
  - role: system-agent-chives
    tags: [system, system-agent-chives]
```

The updated roles section will look like:

```yaml
  - role: system-mcp-gateway
    tags: [system, system-mcp-gateway]
  - role: system-agent-chives
    tags: [system, system-agent-chives]
  - role: monitoring-healthchecksio
    monitoring_healthchecksio_ping_type: success
    tags: [monitoring, monitoring-healthchecksio]
```

- [ ] **Step 3: Commit**

```bash
git add playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml
git commit -m "feat: wire system-agent-chives into Malcolm core playbook"
```

Note: Do not commit the vault file — it is already tracked encrypted. The `ansible-vault edit` command modifies it in place and it should be committed separately if changes were made:

```bash
git add inventory/host_vars/apple-macmini-m4-16gb-malcolm/vault_credentials.yaml
git commit -m "chore: add chives telegram credentials to Malcolm vault"
```

---

### Task 7: Dry-run verification

**Files:** None modified.

- [ ] **Step 1: Run pre-commit across all files**

```bash
pre-commit run --all-files
```

Expected: All checks pass.

- [ ] **Step 2: Run playbook in check mode targeting only the new role**

```bash
ansible-playbook playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml \
  --tags system-agent-chives \
  --check --diff
```

Expected output includes:
- `TASK [system-agent-chives : Unload legacy chives service if running]` — ok (skipped or no change)
- `TASK [system-agent-chives : Remove legacy chives launchd plist]` — ok
- `TASK [system-agent-chives : Ensure chives repo is cloned/updated]` — changed (first run)
- `TASK [system-agent-chives : Deploy .env configuration]` — changed (first run)
- `TASK [system-agent-chives : Deploy launchd plist]` — changed (first run)
- No `FAILED` tasks

Note: `--check` mode cannot actually run `launchctl` or `sqlite3` commands — those tasks will show as skipped or will error in check mode. That is expected. Only the file/template tasks matter here.

- [ ] **Step 3: Run the playbook for real**

```bash
ansible-playbook playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml \
  --tags system-agent-chives
```

Expected: Play completes with no failures. Final task `Ensure service is running` returns `rc=0`.

- [ ] **Step 4: Verify service is live on Malcolm**

```bash
ssh malcolm "launchctl list com.awfulwoman.chives"
```

Expected: Output shows the service PID (non-zero), e.g.:
```
{
	"LimitLoadToSessionType" = "Aqua";
	"Label" = "com.awfulwoman.chives";
	"OnDemand" = false;
	"LastExitStatus" = 0;
	"PID" = 12345;
	...
}
```

- [ ] **Step 5: Spot-check logs on Malcolm**

```bash
ssh malcolm "tail -20 /opt/awfulwoman/chives/logs/chives.log"
```

Expected: chives startup messages with no fatal errors.
