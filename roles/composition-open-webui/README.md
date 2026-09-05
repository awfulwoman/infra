# Open WebUI

[Open WebUI](https://openwebui.com) is a self-hosted web interface to local LLMs through Ollama, and optionally other OpenAI-compatible APIs. It provides a ChatGPT-like UI with conversation history, model management, and user accounts.

The role connects Open WebUI to an Ollama instance through `OLLAMA_BASE_URL`. By default, this points to `llm_default_ollama_base_url` (the Mac Mini, Malcolm), where Ollama runs natively on macOS. If Ollama runs elsewhere, override `composition_open_webui_ollama_base_url` per host.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_open_webui_ollama_base_url` | `{{ llm_default_ollama_base_url }}` | Ollama API endpoint |

## Ports

Internal port `8080`. Exposed via Traefik at `chat.<domain>`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | User data, conversation history, model config |

## DNS

Registers subdomain: `chat`
