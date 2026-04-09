# system-ollama Role Design

**Date:** 2026-04-09
**Status:** Approved

## Overview

An Ansible role that installs ollama, configures it via service-level environment variables, and pulls a specified list of models. Works on both macOS and Ubuntu. Replaces the ad-hoc `ollama` Homebrew formula entry in `bootstrap-macos-server`.

## Role Structure

```
ansible/roles/system-ollama/
├── defaults/
│   └── main.yaml
├── tasks/
│   ├── main.yaml
│   ├── install-macos.yaml
│   └── install-ubuntu.yaml
└── templates/
    ├── launchd.plist.j2
    └── override.conf.j2
```

## Defaults

```yaml
system_ollama_models: []   # per-host model list; each host defines its own
system_ollama_env: {}      # env vars passed to the ollama service
```

## Installation

### macOS (`install-macos.yaml`)

- Install the `ollama` Homebrew formula via `community.general.homebrew`
- Do not use `brew services` — the service is managed directly via a custom launchd plist to retain full control over environment variables
- Deploy `/Library/LaunchDaemons/com.awfulwoman.ollama.plist` from `launchd.plist.j2`
- Load the plist via `launchctl` if not already loaded

### Ubuntu (`install-ubuntu.yaml`)

- Check for `/usr/local/bin/ollama`; run the official install script (`curl -fsSL https://ollama.com/install.sh | sh`) only if absent
- Deploy `/etc/systemd/system/ollama.service.d/override.conf` from `override.conf.j2`
- Ensure the `ollama` systemd service is enabled and started

## Service Configuration

### macOS — `launchd.plist.j2`

- Label: `com.awfulwoman.ollama`
- Program: `/opt/homebrew/bin/ollama serve`
- `RunAtLoad: true`, `KeepAlive: true`
- `EnvironmentVariables` block rendered from `system_ollama_env`; omitted entirely if dict is empty

### Ubuntu — `override.conf.j2`

- Systemd drop-in under `/etc/systemd/system/ollama.service.d/`
- `Environment="KEY=VALUE"` lines rendered from `system_ollama_env` in a `[Service]` block; omitted if dict is empty
- Handler triggers `systemctl daemon-reload` and service restart on change

## Model Pulling

Runs in `tasks/main.yaml` after the OS-specific install include:

```yaml
- name: Pull ollama models
  ansible.builtin.command: "ollama pull {{ item }}"
  loop: "{{ system_ollama_models }}"
  register: result
  changed_when: "'pulling' in result.stdout"
```

- Skipped entirely when `system_ollama_models` is empty
- `ollama pull` is fast (no-op) when model is already up to date; `changed_when` keyed on `pulling` in stdout gives accurate Ansible diff status

## Changes to Existing Roles

- Remove `ollama` from `bootstrap_macos_server_homebrew_formulae` in `ansible/roles/bootstrap-macos-server/defaults/main.yaml`
- Add `system-ollama` to the Malcolm playbook (`ansible/playbooks/baremetal/malcolm/core.yaml`)
- Add `system_ollama_models` to Malcolm host_vars as appropriate
