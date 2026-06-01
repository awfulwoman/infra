# system-mcp-gateway Role Design

**Date:** 2026-06-01
**Target host:** apple-macmini-m4-16gb-malcolm (macOS 15, Sequoia)
**Source app:** https://github.com/awfulwoman/gateway

## Overview

An Ansible role that installs and runs the `gateway` app as a persistent launchd service on malcolm. The gateway is a Python MCP server (SSE/HTTP transport) that exposes email, Calendar, Reminders, Contacts, Obsidian, and Karakeep to Claude Code.

## Approach

The role depends on the gateway repo being present on disk — managed by the existing `system-repos` role. The user adds `awfulwoman/gateway` to `system_repos` in malcolm's host_vars. The role handles everything after the repo is cloned: deps, config, service, and macOS permissions.

## Role Structure

```
roles/system-mcp-gateway/
  defaults/main.yaml
  tasks/main.yaml
  tasks/install-macos.yaml
  templates/env.j2
  templates/launchd.plist.j2
  README.md
```

## Variables

Defined in `defaults/main.yaml`:

| Variable | Default | Notes |
|---|---|---|
| `system_mcp_gateway_repo_dir` | `{{ system_repos_base_dir }}/awfulwoman/gateway` | Where system-repos clones to |
| `system_mcp_gateway_imap_host` | `imap.mailbox.org` | |
| `system_mcp_gateway_imap_port` | `993` | |
| `system_mcp_gateway_imap_username` | `""` | Set in host_vars |
| `system_mcp_gateway_imap_password` | `""` | Set in host_vars from vault |
| `system_mcp_gateway_obsidian_vault_path` | `""` | Set in host_vars |
| `system_mcp_gateway_karakeep_base_url` | `""` | Set in host_vars |
| `system_mcp_gateway_karakeep_api_key` | `""` | Optional, leave empty to disable |
| `system_mcp_gateway_server_host` | `127.0.0.1` | |
| `system_mcp_gateway_server_port` | `4000` | |

### Malcolm host_vars additions (`core.yaml`)

```yaml
system_mcp_gateway_imap_username: "{{ vault_mailprovider_user }}"
system_mcp_gateway_imap_password: "{{ vault_mailprovider_password }}"
system_mcp_gateway_obsidian_vault_path: "{{ ansible_facts.user_dir }}/Obsidian"
system_mcp_gateway_karakeep_base_url: "https://karakeep.{{ domainname_infra }}"
```

Also add to `system_repos` in the same file:
```yaml
- repo: awfulwoman/gateway
```

## Task Sequence (`tasks/install-macos.yaml`)

1. **Install `uv` via Homebrew** — `community.general.homebrew: name=uv state=present`. Malcolm's current homebrew formulae list doesn't include `uv`; the role adds it rather than requiring the operator to update host_vars first.
2. **`uv sync`** — run inside `system_mcp_gateway_repo_dir` to install Python deps from the lock file.
3. **Deploy `.env`** — template `env.j2` → `{{ system_mcp_gateway_repo_dir }}/.env`, mode `0600`. Contains all `GATEWAY_*` env vars.
4. **Ensure logs dir exists** — `{{ system_mcp_gateway_repo_dir }}/logs/`, mode `0755`.
5. **Deploy launchd plist** — template `launchd.plist.j2` → `~/Library/LaunchAgents/com.awfulwoman.gateway.plist`, register result.
6. **Reload service on plist change** — unload then load (same pattern as `system-ollama`, `# noqa: no-handler`).
7. **Ensure service is running** — `launchctl list com.awfulwoman.gateway`, fail if rc != 0.
8. **Grant TCC permissions** — macOS 15 only (skip + debug message otherwise). Uses `sqlite3` on `~/Library/Application Support/com.apple.TCC/TCC.db`. Grants `kTCCServiceCalendar`, `kTCCServiceReminders`, `kTCCServiceAddressBook` to both `org.python.python` (bundle type 0) and the real path of the `uv` binary (bundle type 1). Requires finding the real `uv` path via `which uv` + `python3 -c "import os; print(os.path.realpath(...))"`. All TCC tasks run without `become: true` (TCC.db is per-user).

`tasks/main.yaml` guards the whole thing:
```yaml
- ansible.builtin.include_tasks: install-macos.yaml
  when: ansible_facts['os_family'] == 'Darwin'
```

## Templates

### `env.j2`

Standard `GATEWAY_*` env vars rendered from role variables. All credential fields. Empty vars render as empty strings (gateway skips those integrations).

### `launchd.plist.j2`

Follows `system-ollama` pattern:
- Label: `com.awfulwoman.gateway`
- ProgramArguments: path to `uv`, `run`, `gateway`, `--transport`, `http`
- WorkingDirectory: `{{ system_mcp_gateway_repo_dir }}`
- RunAtLoad: true, KeepAlive: true
- StandardOutPath/StandardErrorPath: `logs/gateway.{log,err}` inside repo
- EnvironmentVariables: PATH including `/opt/homebrew/bin`

## macOS Version Guard for TCC

The TCC step runs only when:
```yaml
when: ansible_facts['distribution_version'] is version('15', '>=') and ansible_facts['distribution_version'] is version('16', '<')
```

If version is outside this range, a `ansible.builtin.debug` message warns the operator to manually grant Calendar/Reminders/Contacts permissions.

## What the Role Does NOT Do

- Clone the repo (handled by `system-repos`)
- Register the MCP server with Claude Code (manual step, documented in README)

## Manual Step After Deployment

After the role runs, register the server once with Claude Code:

```bash
claude mcp add --transport http gateway --scope user http://127.0.0.1:4000/mcp
```

## Playbook Integration

Add to `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`:

```yaml
- role: system-mcp-gateway
  tags: [system, system-mcp-gateway]
```

Placed after `system-repos` (which must have run first to clone the gateway repo).
