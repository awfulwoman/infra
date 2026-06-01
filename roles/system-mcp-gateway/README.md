# system-mcp-gateway

Installs and runs the [gateway](https://github.com/awfulwoman/gateway) MCP server as a launchd service on macOS. Deploys to `/opt/awfulwoman/gateway`.

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_mcp_gateway_base_dir` | `{{ awfulwoman_opt_dir }}` | Base directory for deployed service apps |
| `system_mcp_gateway_repo_dir` | `{{ system_mcp_gateway_base_dir }}/gateway` | Clone destination |
| `system_mcp_gateway_repo_url` | `https://github.com/awfulwoman/gateway.git` | |
| `system_mcp_gateway_repo_version` | `main` | Branch/tag to deploy |
| `system_mcp_gateway_imap_host` | `imap.mailbox.org` | |
| `system_mcp_gateway_imap_port` | `993` | |
| `system_mcp_gateway_imap_username` | `{{ vault_mailprovider_user }}` | Override if needed |
| `system_mcp_gateway_imap_password` | `{{ vault_mailprovider_password }}` | Override if needed |
| `system_mcp_gateway_obsidian_vault_path` | `{{ ansible_facts.user_dir }}/Obsidian` | Override if needed |
| `system_mcp_gateway_karakeep_base_url` | `https://karakeep.{{ domainname_infra }}` | Override if needed |
| `system_mcp_gateway_karakeep_api_key` | `{{ vault_karakeep_api }}` | Override if needed |
| `system_mcp_gateway_server_host` | `127.0.0.1` | |
| `system_mcp_gateway_server_port` | `4000` | |

## After deployment

Register the MCP server with Claude Code once:

```bash
claude mcp add --transport http gateway --scope user http://127.0.0.1:4000/mcp
```

## TCC note

Calendar, Reminders, and Contacts access is granted automatically on macOS 15.x. On other versions, grant access manually in System Settings > Privacy & Security.
