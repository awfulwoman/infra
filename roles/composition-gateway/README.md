# Gateway

Deploys the [`gateway`](https://github.com/awfulwoman/gateway) MCP server + reminders
API as a Docker container, built and published to `ghcr.io/awfulwoman/gateway`.

Serves two surfaces on one port (4000), fronted by a single Traefik router:

- `/mcp` — streamable-HTTP MCP for Claude Code / `chives` / the `gw` CLI, bearer-auth
  via `composition_gateway_server_auth_tokens`.
- `/v1/*` — the native reminders JSON-HTTP API for phone/iPad clients, auth via
  `composition_gateway_reminders_api_tokens`.

Contacts are backed by [`composition-radicale`](../composition-radicale) (CardDAV) —
**not** a role dependency (nesting it in `meta/main.yaml` clobbers this role's own
`composition_root`/`composition_config` facts, redirecting this role's compose file
into Radicale's directory — see the comment in `meta/main.yaml` if tempted to add it
back). Ordering is instead guaranteed by `core.yaml` listing `composition-radicale`
before `composition-gateway`; keep it that way. Gateway reaches it over the shared
Docker network by container name (`http://radicale:5232`); Radicale is never exposed
to Gateway's own clients directly. Contacts work identically on every platform this
image targets — no macOS-only capability gap versus the previous launchd-on-macOS
deployment (it used to depend on `pyobjc`, unavailable in the container; it's now
CardDAV, so it isn't).

Reminders and Calendar are backed by
[`system-apple-reminders-server`](../system-apple-reminders-server) and
[`system-apple-calendar-server`](../system-apple-calendar-server), both running
natively on **Malcolm**, a different host — EventKit needs a macOS GUI session for
the Reminders/Calendar permission grant, so unlike Contacts these can't move into
the container. Gateway reaches both over Tailscale MagicDNS, not the shared Docker
network. Calendar replaces the previous Google Calendar OAuth backend.

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
| `composition_gateway_radicale_base_url/username/password` | `http://radicale:5232` + shared `radicale_username`/`vault_radicale_password` | CardDAV backend for Contacts (see `composition-radicale`) |
| `composition_gateway_radicale_contacts_path` | `/{{ radicale_username }}/contacts/` | CardDAV addressbook collection |
| `composition_gateway_server_auth_tokens` | `vault_gateway_mcp_token` | Bearer token(s) required on `/mcp` |

## Volumes

| Path | Purpose |
|------|---------|
| `composition_gateway_obsidian_vault_path` (host) → `/vault` | Obsidian vault, read/write |

Reminders and Contacts have no local volume here — they live in Radicale's own storage
(see `composition-radicale`'s Volumes table).

## DNS

Registers subdomain: `gateway`
