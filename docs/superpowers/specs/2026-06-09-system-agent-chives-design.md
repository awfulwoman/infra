# system-agent-chives Role Design

**Date:** 2026-06-09
**Status:** Approved

## Overview

A new Ansible role, `system-agent-chives`, that deploys the [chives](https://github.com/awfulwoman/chives) AI agent as a persistent launchd service on macOS (Malcolm). The role follows the pattern established by `system-mcp-gateway`, owning its own clean deployment clone at `/opt/awfulwoman/chives` separate from the dev checkout in `~/Code/awfulwoman/chives`.

Chives is a Telegram-connected AI agent with calendar, reminders, contacts, email, memory, and scheduling tools. It also exposes an OpenWebUI-compatible HTTP API on port 8080.

## File Layout

```
roles/system-agent-chives/
├── defaults/main.yaml
├── tasks/
│   ├── main.yaml           # macOS guard → include install-macos.yaml
│   └── install-macos.yaml
├── templates/
│   ├── env.j2
│   └── launchd.plist.j2
└── README.md
```

## Task Flow (`install-macos.yaml`)

Steps run in this order:

1. **Remove legacy service** — unload `com.chives.agent` (the old `install_service.sh`-managed plist, `failed_when: false`), then remove `~/Library/LaunchAgents/com.chives.agent.plist` (`state: absent`).
2. **Ensure uv installed** via `community.general.homebrew`.
3. **Ensure base dir** `/opt/awfulwoman` exists (become, owner: ansible_user, group: staff, mode 0755).
4. **Clone/update repo** `git@github.com:awfulwoman/chives.git` → `{{ system_agent_chives_repo_dir }}`, register `chives_git`.
5. **Run `uv sync`** in repo dir (`changed_when: false`).
6. **Ensure `logs/` dir** exists within repo dir.
7. **Deploy `.env`** from `env.j2` to `{{ system_agent_chives_repo_dir }}/.env` (mode 0600), register `chives_env`.
8. **Ensure `~/Library/LaunchAgents`** dir exists.
9. **Deploy plist** from `launchd.plist.j2` to `~/Library/LaunchAgents/com.awfulwoman.chives.plist` (mode 0644), register `chives_plist`.
10. **Unload service** (`launchctl unload …`) when any of `chives_plist`, `chives_env`, or `chives_git` changed — `# noqa: no-handler`, `failed_when: false`.
11. **Load service** (`launchctl load …`) under same condition, register `chives_load`, `changed_when: chives_load.rc == 0`.
12. **Verify running** via `launchctl list com.awfulwoman.chives`, `failed_when: rc != 0`.
13. **TCC warning** (debug) if macOS < 15.
14. **Resolve uv symlink** to real path, register `uv_real` (macOS 15+ only).
15. **Grant TCC permissions** for Calendar, Reminders, Contacts via sqlite3 on macOS 15+.

No state or profile data is migrated from the old install. The fresh clone starts clean; chives creates `state/` and `profile/` on first run.

## Variables (`defaults/main.yaml`)

| Variable | Default | Description |
|---|---|---|
| `system_agent_chives_base_dir` | `{{ awfulwoman_opt_dir }}` | Base dir for deployed service apps |
| `system_agent_chives_repo_dir` | `{{ system_agent_chives_base_dir }}/chives` | Clone destination |
| `system_agent_chives_repo_url` | `git@github.com:awfulwoman/chives.git` | |
| `system_agent_chives_repo_version` | `main` | Branch/tag to deploy |
| `system_agent_chives_llm_base_url` | `http://localhost:11434/v1` | Ollama endpoint |
| `system_agent_chives_llm_model` | `gemma4:12b-mlx` | Model for Malcolm |
| `system_agent_chives_llm_api_key` | `ollama` | |
| `system_agent_chives_telegram_token` | `{{ vault_chives_telegram_token }}` | |
| `system_agent_chives_telegram_chat_ids` | `{{ vault_chives_telegram_chat_ids }}` | JSON list |
| `system_agent_chives_imap_host` | `imap.mailbox.org` | |
| `system_agent_chives_imap_port` | `993` | |
| `system_agent_chives_imap_username` | `{{ vault_mailprovider_user }}` | Shared with gateway |
| `system_agent_chives_imap_password` | `{{ vault_mailprovider_password }}` | Shared with gateway |
| `system_agent_chives_morning_brief_time` | `08:00` | |
| `system_agent_chives_event_reminder_minutes` | `15` | |
| `system_agent_chives_idle_checkin_hours` | `0` | |

## Templates

**`env.j2`** — writes `CHIVES_*` env vars using `CHIVES_LLM__*`, `CHIVES_TELEGRAM__*`, `CHIVES_IMAP__*` prefix pattern. Chat IDs rendered via `| to_json` since pydantic-settings expects a JSON list.

**`launchd.plist.j2`** — label `com.awfulwoman.chives`, entry point `uv run python -m chives.main`, working dir `{{ system_agent_chives_repo_dir }}`, RunAtLoad + KeepAlive, stdout/stderr to `logs/chives.log` / `logs/chives.err`.

## TCC Notes

Calendar, Reminders, and Contacts access is granted automatically on macOS 15.x via direct sqlite3 insert (same approach as `system-mcp-gateway`). On earlier versions, grant access manually in System Settings > Privacy & Security.

## Launchd Label Convention

Uses `com.awfulwoman.chives` (not the `com.chives.agent` label from chives's own `install_service.sh`) to stay consistent with the `com.awfulwoman.*` namespace used across this infrastructure.
