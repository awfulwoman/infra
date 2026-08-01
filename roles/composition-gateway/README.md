# Gateway

Deploys the [`gateway`](https://github.com/awfulwoman/gateway) MCP server + reminders
API as a Docker container, built and published to `ghcr.io/awfulwoman/gateway`.

Serves two surfaces on one port (4000), fronted by a single Traefik router:

- `/mcp` — streamable-HTTP MCP for Claude Code / `chives` / the `gw` CLI, bearer-auth
  via `composition_gateway_server_auth_tokens`.
- `/v1/*` — the native reminders JSON-HTTP API for phone/iPad clients, auth via
  `composition_gateway_reminders_api_tokens`.

Reminders, Calendar, and Contacts are backed by
[`system-apple-reminders-server`](../system-apple-reminders-server),
[`system-apple-calendar-server`](../system-apple-calendar-server), and
[`system-apple-contacts-server`](../system-apple-contacts-server), all three
running natively on **Malcolm**, a different host — EventKit/Contacts need a
macOS GUI session for their permission grant, so none of these can move into the
container. Gateway reaches all three over Tailscale MagicDNS, not the shared
Docker network. Calendar replaces the previous Google Calendar OAuth backend;
Contacts replaces the previous Radicale/CardDAV backend.

Obsidian notes/issues tools read/write a vault bind-mounted from the host — this role
does **not** sync that vault itself. Run
[`system-obsidian-headless`](../system-obsidian-headless) on the same host first and
point `composition_gateway_obsidian_vault_path` at its synced vault path.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_gateway_obsidian_vault_path` | *(none — required)* | Host path to a synced Obsidian vault, bind-mounted at `/vault` |
| `composition_gateway_imap_host/username/password` | mailbox.org + vault creds | IMAP account for the Email tool |
| `composition_gateway_calendar_server_base_url` | Malcolm's Tailscale MagicDNS name, port 4101 | apple-calendar-server backend for Calendar (see `system-apple-calendar-server`) |
| `composition_gateway_calendar_server_bearer_token` | `vault_gateway_calendar_server_token` | Shared secret with `system-apple-calendar-server` |
| `composition_gateway_karakeep_base_url/api_key` | karakeep subdomain + vault key | Karakeep bookmarking service |
| `composition_gateway_owntracks_*` | owntracks-recorder subdomain | Location tool |
| `composition_gateway_reminders_api_tokens` | `vault_gateway_reminders_api_token_iphone` | Bearer tokens for `/v1/*` (device clients) |
| `composition_gateway_reminders_server_base_url` | Malcolm's Tailscale MagicDNS name, port 4100 | apple-reminders-server backend for Reminders (see `system-apple-reminders-server`) |
| `composition_gateway_reminders_server_bearer_token` | `vault_gateway_reminders_server_token` | Shared secret with `system-apple-reminders-server` |
| `composition_gateway_contacts_server_base_url` | Malcolm's Tailscale MagicDNS name, port 4102 | apple-contacts-server backend for Contacts (see `system-apple-contacts-server`) |
| `composition_gateway_contacts_server_bearer_token` | `vault_gateway_contacts_server_token` | Shared secret with `system-apple-contacts-server` |
| `composition_gateway_server_auth_tokens` | `vault_gateway_mcp_token` | Bearer token(s) required on `/mcp` |

## Volumes

| Path | Purpose |
|------|---------|
| `composition_gateway_obsidian_vault_path` (host) → `/vault` | Obsidian vault, read/write |

Reminders, Calendar, and Contacts have no local volume here — they live in the real
Reminders/Calendar/Contacts apps on Malcolm, fronted by their own sidecar services.

## DNS

Registers subdomain: `gateway`
