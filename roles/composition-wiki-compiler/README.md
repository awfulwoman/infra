# wiki-compiler

Deploys [`wiki-compiler`](https://github.com/awfulwoman/wiki-compiler), which
compiles the Charlie Obsidian vault and gateway's calendar/bookmarks/
contacts/reminders/location data into an LLM-maintained Obsidian wiki, with
entity pages, wikilinks, and a citation on every fact.

Reached only by container name from other compositions on the same host
(like `composition-mail-archive-server`) — never given a route to the
outside. `composition-wiki-site` builds and serves its output, read-only.

## Volumes

| Host | Container | Purpose |
|---|---|---|
| `composition_wiki_compiler_notes_path` (Charlie Syncthing folder) | `/data/notes` | Notes source, read-only |
| `composition_wiki_compiler_output_path` (PersonalWiki Syncthing folder) | `/data/output` | Compiled wiki pages — the compiler is the only writer |
| `{{ composition_config }}` | `/data/state` | SQLite state (ingested records, dedup, usage log) |

## Key variables

See `defaults/main.yaml` for the full list. The ones with no sane default:

| Variable | Description |
|---|---|
| `composition_wiki_compiler_notes_path` | Host path of the Charlie Syncthing folder — set per host |
| `composition_wiki_compiler_output_path` | Host path of the PersonalWiki Syncthing folder — set per host |
| `vault_gateway_mcp_token_wiki` | This compiler's labelled gateway client token (also added to `composition_gateway_server_auth_clients`) |
| `vault_wiki_compiler_api_token` | Bearer token for the compiler's own `/run`, `/usage`, `/lint`, `/filter-report` HTTP API |
| `vault_wiki_compiler_home_lat` / `_home_lon` / `_home_radius_m` | Optional: enables the home-radius location drop rule. Omit to leave it off |

Generate the required secrets:

```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_gateway_mcp_token_wiki'
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_wiki_compiler_api_token'
```

## Sources and budgets

`composition_wiki_compiler_sources` starts without `email`: the bulk-sender
and noreply filter rules need a `wiki-compiler filter-report` pass on a real
sample before email backfills into the wiki. Flip it on by appending `email`
to the comma-separated list once that's checked.

The model is Malcolm's Ollama serving an Ollama Cloud model
(`llm_default_model`/`llm_default_ollama_base_url`, `group_vars/infra/core.yaml`) —
a metered account shared with the Hermes bots on agatha.
`composition_wiki_compiler_daily_call_budget`/`_daily_token_budget` start
low; raise them after a few days of `docker exec wiki-compiler wiki-compiler usage`.

## Geocoding

`composition_wiki_compiler_geocoder_url` points at the public
`https://nominatim.openstreetmap.org` (the local Nominatim composition
never worked — awfulwoman/infra#299 removes it; `nominatim.org` is only the
project's docs site, not the API — confirmed live). That instance's usage
policy caps requests at 1/second with no key; fine for an hourly backfill of
a handful of location clusters.
