# Gateway

This role deploys the [`gateway`](https://github.com/awfulwoman/gateway) MCP server and reminders
API as a Docker container, built and published to `ghcr.io/awfulwoman/gateway`.

It serves two surfaces on one port (4000), fronted by a single Traefik router:

- `/mcp` — streamable-HTTP MCP for Claude Code, `chives`, and the `gw` CLI, with bearer auth
  through `composition_gateway_server_auth_tokens`.
- `/v1/*` — the native reminders JSON-HTTP API for phone and iPad clients, with auth through
  `composition_gateway_reminders_api_tokens`.

[`system-apple-reminders-server`](../system-apple-reminders-server),
[`system-apple-calendar-server`](../system-apple-calendar-server), and
[`system-apple-contacts-server`](../system-apple-contacts-server) back Reminders,
Calendar, and Contacts. All three run natively on **Malcolm**, a different host,
because EventKit and Contacts need a macOS GUI session for their permission grant. None
of the three can move into the container. Gateway reaches all three over the infra zone
that bertha serves, not the shared Docker network. Calendar replaces the previous
Google Calendar OAuth backend. Contacts replaces the previous Radicale/CardDAV backend.

The Obsidian notes and issues tools read and write a vault bind-mounted from the host.
This role does **not** sync that vault. Run
[`system-obsidian-headless`](../system-obsidian-headless) on the same host first, then
point `composition_gateway_obsidian_vault_path` at its synced vault path.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_gateway_obsidian_vault_path` | *(none — required)* | Host path to a synced Obsidian vault, bind-mounted at `/vault` |
| `composition_gateway_imap_host/username/password` | mailbox.org + vault creds | IMAP account for the Email tool |
| `composition_gateway_calendar_server_base_url` | Malcolm's infra-zone FQDN, port 4101 | apple-calendar-server backend for Calendar (see `system-apple-calendar-server`) |
| `composition_gateway_calendar_server_bearer_token` | `vault_gateway_calendar_server_token` | Shared secret with `system-apple-calendar-server` |
| `composition_gateway_github_repo` | `awfulwoman/meta` | Repo backing the issues tools (`GATEWAY_GITHUB__REPO`) |
| `composition_gateway_github_item_id` | `5edooob5a7kzxkuv5ttu5vdexu` | 1Password item holding the GitHub PAT (`op://Infra/Github`) |
| `composition_gateway_github_token_field` | `gateway_issues_token` | Field on that item read into `GATEWAY_GITHUB__TOKEN` |
| `composition_gateway_karakeep_base_url/api_key` | karakeep subdomain + vault key | Karakeep bookmarking service |
| `composition_gateway_owntracks_*` | owntracks-recorder subdomain | Location tool |
| `composition_gateway_reminders_api_tokens` | `vault_gateway_reminders_api_token_iphone` | Bearer tokens for `/v1/*` (device clients) |
| `composition_gateway_reminders_server_base_url` | Malcolm's infra-zone FQDN, port 4100 | apple-reminders-server backend for Reminders (see `system-apple-reminders-server`) |
| `composition_gateway_reminders_server_bearer_token` | `vault_gateway_reminders_server_token` | Shared secret with `system-apple-reminders-server` |
| `composition_gateway_contacts_server_base_url` | Malcolm's infra-zone FQDN, port 4102 | apple-contacts-server backend for Contacts (see `system-apple-contacts-server`) |
| `composition_gateway_contacts_server_bearer_token` | `vault_gateway_contacts_server_token` | Shared secret with `system-apple-contacts-server` |
| `composition_gateway_server_auth_tokens` | `vault_gateway_mcp_token` | Bearer token(s) required on `/mcp` |

## Secrets

Most credentials come from Ansible Vault. The GitHub PAT for the Issues tool is the
exception: the role fetches it from 1Password Connect at playbook run time
(`op://Infra/Github/gateway_issues_token`) and never stores it in the repo, the same
approach as [`composition-finances`](../composition-finances). To rotate it, change it
in 1Password and run the role again.

## Volumes

| Path | Purpose |
|------|---------|
| `composition_gateway_obsidian_vault_path` (host) → `/vault` | Obsidian vault, read/write |

Reminders, Calendar, and Contacts have no local volume here. They live in the real
Reminders, Calendar, and Contacts apps on Malcolm, fronted by their own sidecar services.

## DNS

Registers subdomain: `gateway`
