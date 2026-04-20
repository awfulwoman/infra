# LibreTranslate

[LibreTranslate](https://libretranslate.com) is a free and open-source machine translation API, providing a self-hosted alternative to Google Translate or DeepL. It supports multiple languages and exposes a REST API and web UI.

The role clones the LibreTranslate source from GitHub and builds the Docker image locally from `{{ composition_config }}/src`. Translation language models are stored in `{{ composition_config }}/models` (mapped to `/home/libretranslate/.local`). A `post_start` hook fixes ownership of the model and API key directories after container start.

## Ports

Internal port `5000`. Exposed via Traefik at `translate.<domain>`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/src` | Cloned LibreTranslate source (used for build) |
| `{{ composition_config }}/models` | Downloaded language models |
| `{{ composition_config }}/apikeys` | API key database |

## DNS

Registers subdomain: `translate`
