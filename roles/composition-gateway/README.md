# Gateway

This role deploys the [`gateway`](https://github.com/awfulwoman/gateway) MCP server and reminders
API as a Docker container, built and published to `ghcr.io/awfulwoman/gateway`.

It serves two surfaces on one port (4000), fronted by a single Traefik router:

- `/mcp` — streamable-HTTP MCP for Claude Code, `chives`, and the `gw` CLI, with bearer auth
  through `composition_gateway_server_auth_clients` (one labelled token per caller).
- `/v1/*` — the native reminders JSON-HTTP API for phone and iPad clients, with auth through
  `composition_gateway_reminders_api_tokens`.

Every `/mcp` request is logged one-JSON-line-per-call (caller label, tool, full arguments,
status, duration) — to `docker compose logs gateway` prefixed `usage `, and to
`{{ composition_root }}/logs/usage.jsonl` (rotating). `/v1/*` is not logged; it is slated for
removal (gateway issue [#1](https://github.com/awfulwoman/gateway/issues/1)).

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
| `composition_gateway_server_auth_clients` | `{jarvis: vault_gateway_mcp_token, laptop: …, gw-cli: …, hermes: …}` | Labelled bearer tokens for `/mcp`; the label is the caller name in the usage log. Empty-valued entries are dropped. |
| `composition_gateway_usage_log_container_path` | `/var/log/gateway/usage.jsonl` | In-container path for the JSONL usage log; bind-mounted from `{{ composition_root }}/logs` |

## Secrets

Most credentials come from Ansible Vault. The GitHub PAT for the Issues tool is the
exception: the role fetches it from 1Password Connect at playbook run time
(`op://Infra/Github/gateway_issues_token`) and never stores it in the repo, the same
approach as [`composition-finances`](../composition-finances). To rotate it, change it
in 1Password and run the role again.

`composition_gateway_server_auth_clients` needs one vault secret per `/mcp` caller.
`jarvis` reuses the existing `vault_gateway_mcp_token` (so
[`composition-jarvis`](../composition-jarvis) is unchanged); the others get their
own secrets in `inventory/group_vars/infra/vault_gateway.yaml`:

```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_gateway_mcp_token_laptop'
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_gateway_mcp_token_gw_cli'
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_gateway_mcp_token_hermes'
```

Each new secret must also be set on the client: `Authorization: Bearer <laptop secret>`
in the laptop's `mcpServers.gateway` config, `GATEWAY_TOKEN=<gw-cli secret>` where the
`gw` CLI runs, and `vault_gateway_mcp_token_hermes` is consumed by
[`composition-hermes-agent`](../composition-hermes-agent) (rendered into its
`.environment_vars` as `GATEWAY_MCP_TOKEN`).

## Volumes

| Path | Purpose |
|------|---------|
| `composition_gateway_obsidian_vault_path` (host) → `/vault` | Obsidian vault, read/write |
| `{{ composition_root }}/logs` (host) → `/var/log/gateway` | `usage.jsonl` request log, rotating |

Reminders, Calendar, and Contacts have no local volume here. They live in the real
Reminders, Calendar, and Contacts apps on Malcolm, fronted by their own sidecar services.

## DNS

Registers subdomain: `gateway`
