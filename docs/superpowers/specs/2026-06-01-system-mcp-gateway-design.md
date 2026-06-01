# system-mcp-gateway Role Design

**Date:** 2026-06-01
**Target host:** apple-macmini-m4-16gb-malcolm (macOS 15, Sequoia)
**Source app:** https://github.com/awfulwoman/gateway

## Overview

An Ansible role that installs and runs the `gateway` app as a persistent launchd service on malcolm. The gateway is a Python MCP server (SSE/HTTP transport) that exposes email, Calendar, Reminders, Contacts, Obsidian, and Karakeep to Claude Code.

## Approach

The role is self-contained: it clones the gateway repo to `/opt/awfulwoman/gateway` and manages the full lifecycle from there. `/opt/awfulwoman/` is the new base for deployed service apps, separate from `~/Code/awfulwoman/` which holds repos the user works in. No dependency on `system-repos`.

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
| `system_mcp_gateway_base_dir` | `{{ awfulwoman_opt_dir }}` | Base for all deployed service apps |
| `system_mcp_gateway_repo_dir` | `{{ system_mcp_gateway_base_dir }}/gateway` | Where the role clones to |
| `system_mcp_gateway_repo_url` | `git@github.com:awfulwoman/gateway.git` | |
| `system_mcp_gateway_repo_version` | `main` | Branch/tag/commit to deploy |
| `system_mcp_gateway_imap_host` | `imap.mailbox.org` | |
| `system_mcp_gateway_imap_port` | `993` | |
| `system_mcp_gateway_imap_username` | `{{ vault_mailprovider_user }}` | Override if needed |
| `system_mcp_gateway_imap_password` | `{{ vault_mailprovider_password }}` | Override if needed |
| `system_mcp_gateway_obsidian_vault_path` | `{{ ansible_facts.user_dir }}/Obsidian` | Override if needed |
| `system_mcp_gateway_karakeep_base_url` | `https://karakeep.{{ domainname_infra }}` | Override if needed |
| `system_mcp_gateway_karakeep_api_key` | `{{ vault_karakeep_api }}` | Override if needed |
| `system_mcp_gateway_server_host` | `127.0.0.1` | |
| `system_mcp_gateway_server_port` | `4000` | |

### Malcolm host_vars

No changes needed — all credential and path defaults resolve correctly from group vars and facts. Override in host_vars only if a host differs from the standard configuration.

## Task Sequence (`tasks/install-macos.yaml`)

1. **Install `uv` via Homebrew** — `community.general.homebrew: name=uv state=present`. Malcolm's current homebrew formulae list doesn't include `uv`; the role adds it directly.
2. **Ensure `/opt/awfulwoman/` exists** — `ansible.builtin.file`, owned by `ansible_user`, group `staff`, mode `0755`. Uses `become: true`.
3. **Clone/update gateway repo** — `ansible.builtin.git` from `system_mcp_gateway_repo_url` to `system_mcp_gateway_repo_dir`, version `system_mcp_gateway_repo_version`. Owned by `ansible_user`.
4. **`uv sync`** — `ansible.builtin.command: uv sync`, `chdir: system_mcp_gateway_repo_dir`. Idempotent via `changed_when`.
5. **Deploy `.env`** — template `env.j2` → `{{ system_mcp_gateway_repo_dir }}/.env`, mode `0600`. Contains all `GATEWAY_*` env vars.
6. **Ensure logs dir exists** — `{{ system_mcp_gateway_repo_dir }}/logs/`, mode `0755`.
7. **Deploy launchd plist** — template `launchd.plist.j2` → `~/Library/LaunchAgents/com.awfulwoman.gateway.plist`, register result.
8. **Reload service on plist change** — unload then load (same pattern as `system-ollama`, `# noqa: no-handler`).
9. **Ensure service is running** — `launchctl list com.awfulwoman.gateway`, fail if rc != 0.
10. **Grant TCC permissions** — macOS 15 only (skip + debug message otherwise). Uses `sqlite3` on `~/Library/Application Support/com.apple.TCC/TCC.db`. Grants `kTCCServiceCalendar`, `kTCCServiceReminders`, `kTCCServiceAddressBook` to both `org.python.python` (bundle type 0) and the real path of the `uv` binary (bundle type 1). Requires finding the real `uv` path via `which uv` + `python3 -c "import os; print(os.path.realpath(...))"`. All TCC tasks run without `become: true` (TCC.db is per-user).

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
- ProgramArguments: `/opt/homebrew/bin/uv`, `run`, `gateway`, `--transport`, `http`
- WorkingDirectory: `{{ system_mcp_gateway_repo_dir }}`
- RunAtLoad: true, KeepAlive: true
- StandardOutPath/StandardErrorPath: `{{ system_mcp_gateway_repo_dir }}/logs/gateway.{log,err}`
- EnvironmentVariables: PATH including `/opt/homebrew/bin`

## macOS Version Guard for TCC

The TCC step runs only when:
```yaml
when: ansible_facts['distribution_version'] is version('15', '>=') and ansible_facts['distribution_version'] is version('16', '<')
```

If version is outside this range, a `ansible.builtin.debug` message warns the operator to manually grant Calendar/Reminders/Contacts permissions.

## What the Role Does NOT Do

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

No ordering constraint relative to `system-repos`.
