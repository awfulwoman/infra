# Gateway

Deploys the [`gateway`](https://github.com/awfulwoman/gateway) MCP server + reminders
API as a Docker container, built and published to `ghcr.io/awfulwoman/gateway`.

Serves two surfaces on one port (4000), fronted by a single Traefik router:

- `/mcp` — streamable-HTTP MCP for Claude Code / `chives` / the `gw` CLI, bearer-auth
  via `composition_gateway_server_auth_tokens`.
- `/v1/*` — the native reminders JSON-HTTP API for phone/iPad clients, auth via
  `composition_gateway_reminders_api_tokens`.

Reminders data lives in `{{ composition_config }}/db`. Obsidian notes/issues tools
read/write a vault bind-mounted from the host — this role does **not** sync that vault
itself. Run [`system-obsidian-headless`](../system-obsidian-headless) on the same host
first and point `composition_gateway_obsidian_vault_path` at its synced vault path.

The macOS-native Contacts tool group is unavailable in this container (the image is
built without `pyobjc`); this is the one capability lost versus the previous
launchd-on-macOS deployment.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_gateway_obsidian_vault_path` | *(none — required)* | Host path to a synced Obsidian vault, bind-mounted at `/vault` |
| `composition_gateway_imap_host/username/password` | mailbox.org + vault creds | IMAP account for the Email tool |
| `composition_gateway_gcal_token_json` | `vault_gateway_gcal_token_json` | Google Calendar OAuth credentials JSON (see gateway repo's README for bootstrap) |
| `composition_gateway_karakeep_base_url/api_key` | karakeep subdomain + vault key | Karakeep bookmarking service |
| `composition_gateway_owntracks_*` | owntracks-recorder subdomain | Location tool |
| `composition_gateway_reminders_api_tokens` | `vault_gateway_reminders_api_token_iphone` | Bearer tokens for `/v1/*` (device clients) |
| `composition_gateway_server_auth_tokens` | `vault_gateway_mcp_token` | Bearer token(s) required on `/mcp` |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/db` | Reminders SQLite database |
| `composition_gateway_obsidian_vault_path` (host) → `/vault` | Obsidian vault, read/write |

## DNS

Registers subdomain: `gateway`
