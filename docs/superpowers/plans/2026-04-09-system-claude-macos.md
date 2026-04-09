# system-claude macOS Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the `system-claude` Ansible role to support macOS (malcolm) alongside the existing Ubuntu setup, using platform-dispatched include files.

**Architecture:** `main.yaml` dispatches to `install-macos.yaml` or `install-ubuntu.yaml` via `ansible_facts['os_family']`, matching the `system-ollama` pattern in this repo. All shared tasks (Claude CLI install, PATH, settings dir, env vars, tmux) stay in `main.yaml`. A new `system_claude_settings_group` var handles the macOS vs Ubuntu group ownership difference.

**Tech Stack:** Ansible, `community.general.homebrew` (macOS), `ansible.builtin.apt` (Ubuntu), `ansible-lint`

---

## File Map

| Action | File |
|--------|------|
| Create | `ansible/roles/system-claude/tasks/install-ubuntu.yaml` |
| Create | `ansible/roles/system-claude/tasks/install-macos.yaml` |
| Modify | `ansible/roles/system-claude/tasks/main.yaml` |
| Modify | `ansible/roles/system-claude/defaults/main.yaml` |
| Modify | `ansible/inventory/host_vars/deedee/core.yaml` |
| Modify | `ansible/inventory/host_vars/malcolm/core.yaml` |
| Modify | `ansible/playbooks/baremetal/malcolm/core.yaml` |

---

## Task 1: Create install-ubuntu.yaml

Extract the Ubuntu-specific tasks from the current `main.yaml` verbatim.

**Files:**
- Create: `ansible/roles/system-claude/tasks/install-ubuntu.yaml`

- [ ] **Step 1: Create the file**

```yaml
---
- name: Ensure dependencies are installed
  become: true
  ansible.builtin.apt:
    name:
      - curl
      - gpg
      - yt-dlp
      - bubblewrap
      - socat
      - libonig-dev
    state: present

- name: Add GitHub CLI repository key
  become: true
  ansible.builtin.apt_key:
    url: https://cli.github.com/packages/githubcli-archive-keyring.gpg
    keyring: /usr/share/keyrings/githubcli-archive-keyring.gpg
    state: present

- name: Add GitHub CLI repository
  become: true
  ansible.builtin.apt_repository:
    repo: "deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main"
    filename: github-cli
    state: present

- name: Install GitHub CLI
  become: true
  ansible.builtin.apt:
    name: gh
    state: present
    update_cache: true
```

- [ ] **Step 2: Lint**

Run: `cd ansible && ansible-lint roles/system-claude/tasks/install-ubuntu.yaml`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/system-claude/tasks/install-ubuntu.yaml
git commit -m "feat(system-claude): extract ubuntu install tasks to install-ubuntu.yaml"
```

---

## Task 2: Create install-macos.yaml

Install the equivalent packages via Homebrew. `bubblewrap` and `libonig-dev` have no macOS equivalent and are omitted. `curl` and `gpg` ship with macOS.

**Files:**
- Create: `ansible/roles/system-claude/tasks/install-macos.yaml`

- [ ] **Step 1: Create the file**

```yaml
---
- name: Ensure dependencies are installed (macOS)
  community.general.homebrew:
    name:
      - socat
      - yt-dlp
      - gh
    state: present
```

- [ ] **Step 2: Lint**

Run: `cd ansible && ansible-lint roles/system-claude/tasks/install-macos.yaml`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/system-claude/tasks/install-macos.yaml
git commit -m "feat(system-claude): add macos install tasks via homebrew"
```

---

## Task 3: Rewrite main.yaml

Replace the Ubuntu-specific tasks at the top with a dispatch block. Fix the settings dir task to use `system_claude_settings_group` (required because macOS primary group is `staff`, not the username).

**Files:**
- Modify: `ansible/roles/system-claude/tasks/main.yaml`

- [ ] **Step 1: Replace the file contents**

```yaml
---
- name: Install dependencies (macOS)
  ansible.builtin.include_tasks: install-macos.yaml
  when: ansible_facts['os_family'] == 'Darwin'

- name: Install dependencies (Ubuntu/Debian)
  ansible.builtin.include_tasks: install-ubuntu.yaml
  when: ansible_facts['os_family'] == 'Debian'

- name: Check if Claude CLI is already installed
  ansible.builtin.stat:
    path: "{{ ansible_facts.user_dir }}/.local/bin/claude"
  register: claude_installed

- name: Install Claude CLI
  when: not claude_installed.stat.exists
  block:
    - name: Download and execute Claude CLI install script
      ansible.builtin.shell: >
        curl -fsSL {{ system_claude_install_url }} | bash -s -- {{ system_claude_channel }}
      args:
        creates: "{{ ansible_facts.user_dir }}/.local/bin/claude"
        executable: /bin/bash
      environment:
        HOME: "{{ ansible_facts.user_dir }}"

- name: Ensure .local/bin is in PATH
  when: system_claude_ensure_path
  block:
    - name: Check if PATH export already exists in profile
      ansible.builtin.lineinfile:
        path: "{{ ansible_facts.user_dir }}/{{ system_claude_profile_file }}"
        regexp: '^export PATH="\$HOME/\.local/bin:\$PATH"'
        state: absent
      check_mode: true
      register: path_check
      changed_when: false

    - name: Add .local/bin to PATH in shell profile
      ansible.builtin.lineinfile:
        path: "{{ ansible_facts.user_dir }}/{{ system_claude_profile_file }}"
        line: 'export PATH="$HOME/.local/bin:$PATH"'
        create: true
        mode: '0644'
      when: path_check.found == 0

- name: Ensure Claude settings path exists
  become: true
  ansible.builtin.file:
    path: "{{ system_claude_settings_path }}"
    state: directory
    owner: "{{ ansible_user }}"
    group: "{{ system_claude_settings_group }}"
    mode: "0755"

- name: Set environment variables
  ansible.builtin.lineinfile:
    path: "{{ ansible_facts.user_dir }}/{{ system_claude_profile_file }}"
    line: "export {{ item }}"
    create: true
    mode: '0644'
  loop:
    - "ANTHROPIC_MODEL=claude-sonnet-4-6"
    - "CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false"
    - "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1"
    - "CLAUDE_CONFIG_DIR={{ system_claude_settings_path }}"
    # - "CLAUDE_CODE_OAUTH_TOKEN={{ vault_claudecode_longlived_token }}"

# Allows scrolling in tmux
- name: Enable tmux mouse mode
  ansible.builtin.lineinfile:
    path: "{{ ansible_facts.user_dir }}/.tmux.conf"
    line: "set -g mouse on"
    create: true
    mode: "0644"
```

- [ ] **Step 2: Lint**

Run: `cd ansible && ansible-lint roles/system-claude/tasks/main.yaml`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/system-claude/tasks/main.yaml
git commit -m "feat(system-claude): dispatch to platform-specific install tasks, add settings group var"
```

---

## Task 4: Update defaults/main.yaml

Change the `system_claude_settings_path` default to a neutral cross-platform value. Add `system_claude_settings_group` defaulting to `{{ ansible_user }}` (correct for Ubuntu; overridden for macOS).

**Files:**
- Modify: `ansible/roles/system-claude/defaults/main.yaml`

- [ ] **Step 1: Replace the file contents**

```yaml
---
# Claude CLI installation URL
system_claude_install_url: "https://claude.ai/install.sh"

# Claude CLI version channel (stable, latest, or specific version)
system_claude_channel: "latest"

# Ensure PATH is set in shell profile
system_claude_ensure_path: true

# Shell profile file to update (default: .bashrc for Ubuntu)
system_claude_profile_file: ".bashrc"

# Directory for Claude settings and config
system_claude_settings_path: "~/.config/claude"

# Group owner for the settings directory
# Ubuntu: matches ansible_user (users have an eponymous group)
# macOS: override to "staff" in host_vars
system_claude_settings_group: "{{ ansible_user }}"
```

- [ ] **Step 2: Lint**

Run: `cd ansible && ansible-lint roles/system-claude/`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/system-claude/defaults/main.yaml
git commit -m "fix(system-claude): neutral default for settings_path, add settings_group var"
```

---

## Task 5: Pin settings path in host_vars/deedee

The role default changed to `~/.config/claude`. Deedee uses a ZFS dataset at `/fastpool/claude/settings` — pin it explicitly so nothing changes for the existing host.

**Files:**
- Modify: `ansible/inventory/host_vars/deedee/core.yaml`

- [ ] **Step 1: Add the var**

At the bottom of `ansible/inventory/host_vars/deedee/core.yaml`, append:

```yaml
# -------------------------------------------------------------------
# CLAUDE
# -------------------------------------------------------------------
system_claude_settings_path: "/fastpool/claude/settings"
```

- [ ] **Step 2: Commit**

```bash
git add ansible/inventory/host_vars/deedee/core.yaml
git commit -m "fix(deedee): pin system_claude_settings_path to ZFS location"
```

---

## Task 6: Add Claude vars to host_vars/malcolm

Malcolm is macOS, so it needs a `.zshrc` profile, `/opt/claude` settings path, and `staff` as the settings group.

**Files:**
- Modify: `ansible/inventory/host_vars/malcolm/core.yaml`

- [ ] **Step 1: Add the vars**

At the bottom of `ansible/inventory/host_vars/malcolm/core.yaml`, append:

```yaml
# -------------------------------------------------------------------
# CLAUDE
# -------------------------------------------------------------------
system_claude_settings_path: "/opt/claude"
system_claude_settings_group: "staff"
system_claude_profile_file: ".zshrc"
```

- [ ] **Step 2: Commit**

```bash
git add ansible/inventory/host_vars/malcolm/core.yaml
git commit -m "feat(malcolm): add system-claude host vars for macos"
```

---

## Task 7: Add system-claude to malcolm's playbook

**Files:**
- Modify: `ansible/playbooks/baremetal/malcolm/core.yaml`

- [ ] **Step 1: Add the role**

Replace the file contents with:

```yaml
---
- name: Malcolm
  hosts: malcolm
  roles:
    - role: bootstrap-macos-server
    - role: automation-key-updater
    - role: system-ollama
    - role: system-claude
```

- [ ] **Step 2: Lint**

Run: `cd ansible && ansible-lint playbooks/baremetal/malcolm/core.yaml`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add ansible/playbooks/baremetal/malcolm/core.yaml
git commit -m "feat(malcolm): add system-claude role"
```

---

## Task 8: Dry run against both hosts

Verify the role behaves correctly on both Ubuntu (deedee) and macOS (malcolm) without making changes.

- [ ] **Step 1: Check run against deedee**

Run:
```bash
ansible-playbook ansible/playbooks/baremetal/deedee/core.yaml --check --diff
```
Expected: tasks show as ok/changed with no errors. The apt tasks should appear, homebrew tasks should be skipped.

- [ ] **Step 2: Check run against malcolm**

Run:
```bash
ansible-playbook ansible/playbooks/baremetal/malcolm/core.yaml --check --diff
```
Expected: homebrew tasks appear, apt tasks are skipped. Settings path shows `/opt/claude`, profile file shows `.zshrc`.

- [ ] **Step 3: Apply to malcolm**

Once check passes, run for real:
```bash
ansible-playbook ansible/playbooks/baremetal/malcolm/core.yaml
```
Expected: all tasks complete without errors. SSH to malcolm and verify:
```bash
which claude && echo $CLAUDE_CONFIG_DIR && ls /opt/claude
```
