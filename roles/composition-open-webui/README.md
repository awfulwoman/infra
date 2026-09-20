# Open WebUI

[Open WebUI](https://openwebui.com) is a self-hosted web interface to local LLMs through Ollama, and optionally other OpenAI-compatible APIs. It provides a ChatGPT-like UI with conversation history, model management, and user accounts.

The role connects Open WebUI to an Ollama instance through `OLLAMA_BASE_URL`. By default, this points to `llm_default_ollama_base_url` (the Mac Mini, Malcolm), where Ollama runs natively on macOS. If Ollama runs elsewhere, override `composition_open_webui_ollama_base_url` per host.

## OpenAI-compatible endpoints

`composition_open_webui_openai_apis` adds backends that are not Ollama - anything serving `/v1/models` and `/v1/chat/completions`. Each entry is a `{url, key}` pair:

```yaml
composition_open_webui_openai_apis:
  - url: "http://hermes-jarvis:8642/v1"
    key: "{{ vault_hermes_jarvis_api_server_key }}"
```

Open WebUI consumes these as two semicolon-separated env lists (`OPENAI_API_BASE_URLS`, `OPENAI_API_KEYS`) **paired up by position**, so an entry missing its key would silently shift every later endpoint onto the wrong credential. `tasks/main.yaml` asserts both fields are present on every entry rather than letting that happen. An empty list sets `ENABLE_OPENAI_API=False` and leaves Ollama as the only backend.

Because the pairing is positional and the keys are real credentials, `.environment_vars` is written `0600` and `no_log`, unlike the rest of this role's files.

A bare container name (`hermes-jarvis`) only resolves for a composition on the **same host**, over `{{ default_docker_network }}`. Reaching one on another host means going through its Traefik endpoint by name instead.

### Fronting an agent

The endpoint does not have to be a plain inference server. [`composition-hermes-jarvis`](../composition-hermes-jarvis) can expose its agent on an OpenAI-compatible port (`composition_hermes_jarvis_api_server`), which makes Open WebUI a front end for the agent - tools, memory and all - rather than for a bare model. Hermes maps a stateless chat completion onto one of its own sessions by fingerprinting the conversation, specifically so clients like this one get continuity; its dashboard stays the place for approvals, skills and cron.

## Config persistence, and why rotation needs it off

Open WebUI's environment variables are a **first-boot seed only**. On start it copies them into the `config` table in `webui.db`, and from then on the database wins - `models/config.py`'s `seed_defaults` says so outright ("Existing DB values take precedence over defaults") and inserts only `if key not in existing_keys`.

This silently breaks key rotation. Change `vault_hermes_jarvis_api_server_key`, redeploy, and Hermes starts accepting only the new key while Open WebUI keeps presenting the old one from its database - every place you would check (the vault, both `.environment_vars` files, `docker exec … printenv`) shows the new value, and the endpoint still 401s.

`composition_open_webui_persistent_config: false` (the default here) sets `ENABLE_PERSISTENT_CONFIG=False`, which makes `persistent_enabled_for()` return False for every key, so `Config.get()` returns the env-derived default on each boot and this role stays authoritative.

The trade-off is not scoped to keys: **settings changed in the admin UI stop surviving restarts**, reverting to whatever the role sets. Chats, users, models and prompts live in separate tables and are unaffected. Set it to `true` if you would rather configure through the UI - and then rotate keys in the UI too, or clear the `openai.api_keys` row from `webui.db`, because a redeploy will not do it.

Rows already written to `config` by an earlier boot are simply ignored while this is off; they do not need clearing.

## Authentication

`composition_open_webui_auth` maps to `WEBUI_AUTH`, and is `true`. The role ran with it off historically, on the assumption the host is only reachable over Tailscale - but Tailscale governs who reaches the host, not what they may drive once there, and an entry in `composition_open_webui_openai_apis` can be an agent with a shell (Hermes runs its terminal toolset inside its own container). With auth off, anyone who opens the UI inherits that.

The first account created becomes the admin. Open the site and register before anyone else does.

The flag only travels one way on a live install: Open WebUI refuses to disable auth once any user exists in its database, so going back to `false` later means clearing the data directory first. Going `false` -> `true` is fine at any point, and needs no reset - though an install that ran with auth off may hold an auto-created account, so check `user` and `auth` in `webui.db` before flipping, or you get a login prompt for a password nobody has.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_open_webui_ollama_base_url` | `{{ llm_default_ollama_base_url }}` | Ollama API endpoint |
| `composition_open_webui_openai_apis` | `[]` | `{url, key}` pairs for OpenAI-compatible backends |
| `composition_open_webui_auth` | `false` | `WEBUI_AUTH` - see above |

## Ports

Internal port `8080`. Exposed via Traefik at `chat.<domain>`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | User data, conversation history, model config |

## DNS

Registers subdomain: `chat`

## Removing it

Set `state: absent` on the host's `compositions:` entry and run the play. That stops the project and deletes the data directory (accounts, chat history, model config), the compose file and `.environment_vars`. The ZFS dataset is deliberately left behind - destroy it by hand once you are sure:

```bash
sudo zfs destroy -r <pool>/compositions/open-webui
```

Then drop the entry from `compositions:` and re-run `infra-named` on bertha to retire the `chat` CNAME.

## Moving it to another host

`roles/infra-named`'s `dns_records` filter refuses to derive DNS when two hosts claim the same label, and it does not skip entries marked `state: absent`. So a move is two passes, not one:

1. Set `state: absent` on the old host and run its play. Then **delete** the entry.
2. Add the composition to the new host and run that play.
3. Run `infra-named` on bertha to repoint the `chat` CNAME.

Adding it to the new host before deleting it from the old one leaves the inventory in a state where `infra-named` fails with `DuplicateLabelError`.
