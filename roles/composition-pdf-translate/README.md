# PDF Translate

Runs [pdf-translate](https://github.com/jctots/pdf-translate): upload a PDF and get a translated PDF with the original layout. It has a Gradio UI and a REST API on the same port.

## Endpoint

`https://pdf-translate.<domainname_infra>` (internal DNS via `composition_dns_subdomains`, TLS via Traefik). The app has no login, so the endpoint is internal only.

- UI: `/`
- API: `/api/translate`, `/api/health`, Swagger at `/docs`

## Translation backend

Ollama on Malcolm (`llm_default_ollama_base_url`), model `translategemma:4b`. Malcolm pulls the model through `system_ollama_models`. LibreTranslate is not used for translation.

Paperless's automatic translations always use the local model, so documents stay on the LAN. For a better translation of a document you are happy to send to Ollama's cloud, open **Backend settings** in the UI and set **Translation model** to `gemma4:31b-cloud` for that run. It fixed the 4b model's small errors in testing, at the same speed. Do not click **Save configuration** with a cloud model set: that makes it the UI default.

## Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_pdf_translate_ollama_url` | `{{ llm_default_ollama_base_url }}` | Ollama API URL |
| `composition_pdf_translate_ollama_model` | `translategemma:4b` | Translation model |
| `composition_pdf_translate_block_timeout` | `300.0` | Seconds per Ollama call. Upstream hard-codes 30, which is too short for long text blocks on Malcolm. The compose `command` patches it at start |
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
