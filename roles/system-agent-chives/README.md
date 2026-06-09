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
