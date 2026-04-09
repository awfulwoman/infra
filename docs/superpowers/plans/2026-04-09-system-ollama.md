# system-ollama Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an Ansible role that installs ollama, configures it via service env vars, and pulls a specified model list on both macOS and Ubuntu.

**Architecture:** OS-specific install task files (`install-macos.yaml`, `install-ubuntu.yaml`) are dispatched from `tasks/main.yaml` based on `ansible_facts['os_family']`. Service config is managed via a custom launchd plist on macOS and a systemd drop-in on Ubuntu. Model pulling runs as shared logic after the OS-specific install.

**Tech Stack:** Ansible, Jinja2 templates, Homebrew (macOS), systemd (Ubuntu), launchd (macOS)

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `ansible/roles/system-ollama/defaults/main.yaml` | Default variable values |
| Create | `ansible/roles/system-ollama/tasks/main.yaml` | OS dispatch + model pulling |
| Create | `ansible/roles/system-ollama/tasks/install-macos.yaml` | Homebrew install + launchd service |
| Create | `ansible/roles/system-ollama/tasks/install-ubuntu.yaml` | Install script + systemd service |
| Create | `ansible/roles/system-ollama/handlers/main.yaml` | Ubuntu systemd restart handler |
| Create | `ansible/roles/system-ollama/templates/launchd.plist.j2` | macOS launchd service definition |
| Create | `ansible/roles/system-ollama/templates/override.conf.j2` | Ubuntu systemd env var drop-in |
| Modify | `ansible/roles/bootstrap-macos-server/defaults/main.yaml` | Remove `ollama` from Homebrew formulae |
| Modify | `ansible/playbooks/baremetal/malcolm/core.yaml` | Add `system-ollama` role |
| Modify | `ansible/inventory/host_vars/malcolm/core.yaml` | Add `system_ollama_models` list |

---

## Task 1: Scaffold defaults

**Files:**
- Create: `ansible/roles/system-ollama/defaults/main.yaml`

- [ ] **Step 1: Create the defaults file**

```yaml
---
system_ollama_models: []
system_ollama_env: {}
```

- [ ] **Step 2: Lint**

```bash
source .venv/bin/activate
ansible-lint ansible/roles/system-ollama/defaults/main.yaml
```

Expected: no errors (may warn about missing tasks — that's fine at this stage).

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/system-ollama/defaults/main.yaml
git commit -m "feat(system-ollama): scaffold role defaults"
```

---

## Task 2: launchd plist template (macOS)

**Files:**
- Create: `ansible/roles/system-ollama/templates/launchd.plist.j2`

- [ ] **Step 1: Create the template**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.awfulwoman.ollama</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/ollama</string>
        <string>serve</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
{% if system_ollama_env %}
    <key>EnvironmentVariables</key>
    <dict>
{% for key, value in system_ollama_env.items() %}
        <key>{{ key }}</key>
        <string>{{ value }}</string>
{% endfor %}
    </dict>
{% endif %}
</dict>
</plist>
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/system-ollama/templates/launchd.plist.j2
git commit -m "feat(system-ollama): add launchd plist template"
```

---

## Task 3: systemd drop-in template (Ubuntu)

**Files:**
- Create: `ansible/roles/system-ollama/templates/override.conf.j2`

- [ ] **Step 1: Create the template**

```ini
{% if system_ollama_env %}
[Service]
{% for key, value in system_ollama_env.items() %}
Environment="{{ key }}={{ value }}"
{% endfor %}
{% endif %}
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/system-ollama/templates/override.conf.j2
git commit -m "feat(system-ollama): add systemd drop-in template"
```

---

## Task 4: macOS install tasks

**Files:**
- Create: `ansible/roles/system-ollama/tasks/install-macos.yaml`

- [ ] **Step 1: Create the task file**

```yaml
---
- name: Ensure ollama is installed via Homebrew
  community.general.homebrew:
    name: ollama
    state: present

- name: Ensure launchd plist is deployed
  become: true
  ansible.builtin.template:
    src: launchd.plist.j2
    dest: /Library/LaunchDaemons/com.awfulwoman.ollama.plist
    owner: root
    group: wheel
    mode: "0644"
  register: ollama_plist

- name: Unload service before reload on plist change
  become: true
  ansible.builtin.command: launchctl unload /Library/LaunchDaemons/com.awfulwoman.ollama.plist
  when: ollama_plist.changed
  changed_when: false
  failed_when: false

- name: Ensure service is loaded
  become: true
  ansible.builtin.command: launchctl load /Library/LaunchDaemons/com.awfulwoman.ollama.plist
  register: launchctl_load
  changed_when: launchctl_load.rc == 0
  failed_when: false
```

- [ ] **Step 2: Lint**

```bash
source .venv/bin/activate
ansible-lint ansible/roles/system-ollama/tasks/install-macos.yaml
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/system-ollama/tasks/install-macos.yaml
git commit -m "feat(system-ollama): add macOS install tasks"
```

---

## Task 5: Ubuntu install tasks + handler

**Files:**
- Create: `ansible/roles/system-ollama/tasks/install-ubuntu.yaml`
- Create: `ansible/roles/system-ollama/handlers/main.yaml`

- [ ] **Step 1: Create the Ubuntu task file**

```yaml
---
- name: Check if ollama binary exists
  ansible.builtin.stat:
    path: /usr/local/bin/ollama
  register: ollama_binary

- name: Install ollama via official script
  become: true
  ansible.builtin.shell:
    cmd: curl -fsSL https://ollama.com/install.sh | sh
  when: not ollama_binary.stat.exists
  changed_when: true

- name: Ensure systemd override directory exists
  become: true
  ansible.builtin.file:
    path: /etc/systemd/system/ollama.service.d
    state: directory
    owner: root
    group: root
    mode: "0755"

- name: Deploy systemd env var override
  become: true
  ansible.builtin.template:
    src: override.conf.j2
    dest: /etc/systemd/system/ollama.service.d/override.conf
    owner: root
    group: root
    mode: "0644"
  notify: Restart ollama

- name: Ensure ollama service is enabled and started
  become: true
  ansible.builtin.systemd:
    name: ollama
    enabled: true
    state: started
```

- [ ] **Step 2: Create the handler file**

```yaml
---
- name: Restart ollama
  become: true
  ansible.builtin.systemd:
    name: ollama
    state: restarted
    daemon_reload: true
```

- [ ] **Step 3: Lint both files**

```bash
source .venv/bin/activate
ansible-lint ansible/roles/system-ollama/tasks/install-ubuntu.yaml
ansible-lint ansible/roles/system-ollama/handlers/main.yaml
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add ansible/roles/system-ollama/tasks/install-ubuntu.yaml ansible/roles/system-ollama/handlers/main.yaml
git commit -m "feat(system-ollama): add Ubuntu install tasks and handler"
```

---

## Task 6: Main tasks file

**Files:**
- Create: `ansible/roles/system-ollama/tasks/main.yaml`

- [ ] **Step 1: Create the main task file**

```yaml
---
- name: Install ollama (macOS)
  ansible.builtin.include_tasks: install-macos.yaml
  when: ansible_facts['os_family'] == 'Darwin'

- name: Install ollama (Ubuntu/Debian)
  ansible.builtin.include_tasks: install-ubuntu.yaml
  when: ansible_facts['os_family'] == 'Debian'

- name: Pull ollama models
  ansible.builtin.command: "ollama pull {{ item }}"
  loop: "{{ system_ollama_models }}"
  register: result
  changed_when: "'pulling' in result.stdout"
```

- [ ] **Step 2: Lint the whole role**

```bash
source .venv/bin/activate
ansible-lint ansible/roles/system-ollama/
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/system-ollama/tasks/main.yaml
git commit -m "feat(system-ollama): add main tasks with OS dispatch and model pulling"
```

---

## Task 7: Wire up Malcolm and remove ollama from bootstrap-macos-server

**Files:**
- Modify: `ansible/roles/bootstrap-macos-server/defaults/main.yaml`
- Modify: `ansible/playbooks/baremetal/malcolm/core.yaml`
- Modify: `ansible/inventory/host_vars/malcolm/core.yaml`

- [ ] **Step 1: Remove `ollama` from bootstrap-macos-server defaults**

Edit `ansible/roles/bootstrap-macos-server/defaults/main.yaml` to:

```yaml
---
bootstrap_macos_server_homebrew_formulae:
  - jq
  - git
  - watch
```

- [ ] **Step 2: Add system-ollama to the Malcolm playbook**

Edit `ansible/playbooks/baremetal/malcolm/core.yaml` to:

```yaml
- name: Malcolm
  hosts: malcolm
  roles:
    - role: bootstrap-macos-server
    - role: automation-key-updater
    - role: system-ollama
```

- [ ] **Step 3: Add system_ollama_models to Malcolm host_vars**

Append to `ansible/inventory/host_vars/malcolm/core.yaml`:

```yaml
# -------------------------------------------------------------------
# OLLAMA
# -------------------------------------------------------------------
system_ollama_models:
  - llama3.2
```

(Adjust model name to whatever is actually desired for malcolm.)

- [ ] **Step 4: Lint the playbook**

```bash
source .venv/bin/activate
ansible-lint ansible/playbooks/baremetal/malcolm/core.yaml
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add \
  ansible/roles/bootstrap-macos-server/defaults/main.yaml \
  ansible/playbooks/baremetal/malcolm/core.yaml \
  ansible/inventory/host_vars/malcolm/core.yaml
git commit -m "feat(system-ollama): wire up malcolm, remove ollama from bootstrap-macos-server"
```

---

## Task 8: Run playbook against malcolm

- [ ] **Step 1: Run in check mode first**

```bash
source .venv/bin/activate
ansible-playbook ansible/playbooks/baremetal/malcolm/core.yaml --check
```

Expected: play runs without fatal errors. Some tasks may show `skipping` (Ubuntu tasks on macOS host — expected).

- [ ] **Step 2: Run for real**

```bash
source .venv/bin/activate
ansible-playbook ansible/playbooks/baremetal/malcolm/core.yaml
```

Expected: all tasks pass. Model pull task shows `changed` on first run, `ok` on subsequent runs.

- [ ] **Step 3: Verify ollama is serving on malcolm**

```bash
ssh malcolm 'curl -s http://localhost:11434'
```

Expected: `Ollama is running`
