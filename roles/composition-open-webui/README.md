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

## Authentication

`composition_open_webui_auth` maps to `WEBUI_AUTH`, and is `false` - the historical setting for this role, on the assumption the host is only reachable over Tailscale.

Turn it on when an agent endpoint is wired in. With auth off, anyone who reaches the UI inherits whatever that agent can do, which in Hermes' case includes a shell inside its container. The first account created after switching it on becomes the admin.

The flag only travels one way on a live install: Open WebUI refuses to disable auth once any user exists in its database, so going back to `false` later means clearing the data directory first. Going `false` -> `true` is fine at any point.

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
