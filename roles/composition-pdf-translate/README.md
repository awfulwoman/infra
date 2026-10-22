# PDF Translate

Runs [pdf-translate](https://github.com/jctots/pdf-translate): upload a PDF and get a translated PDF with the original layout. It has a Gradio UI and a REST API on the same port.

## Endpoint

`https://pdf-translate.<domainname_infra>` (internal DNS via `composition_dns_subdomains`, TLS via Traefik). The app has no login, so the endpoint is internal only.

- UI: `/`
- API: `/api/translate`, `/api/health`, Swagger at `/docs`

## Translation backend

Ollama on Malcolm (`llm_default_ollama_base_url`), model `translategemma:12b`. Malcolm pulls the model through `system_ollama_models`. LibreTranslate is not used for translation.

## Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_pdf_translate_ollama_url` | `{{ llm_default_ollama_base_url }}` | Ollama API URL |
| `composition_pdf_translate_ollama_model` | `translategemma:12b` | Translation model |
| `composition_pdf_translate_block_timeout` | `300.0` | Seconds per Ollama call. Upstream hard-codes 30, which is too short for the 12b model on Malcolm (~12 tokens/s). The compose `command` patches it at start |
| `composition_pdf_translate_source_lang` | `de` | UI default source language |
| `composition_pdf_translate_target_lang` | `en` | UI default target language |

These seed `config/data/config.json` once (`force: false`). After that, the UI's **Save configuration** button owns the file. Delete it and redeploy to reset. The REST API ignores `config.json`: callers send all settings with each request.

## Paperless

`composition-paperless-ngx` runs the `pdf-translate-webhook` sidecar, which calls this service for each new German document. See that role's README.

## Data

Only `config.json` is stored. ZFS policy `none`.

## Deploy

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags composition -e target_composition=pdf-translate
```
