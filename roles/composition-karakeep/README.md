# Karakeep

[Karakeep](https://karakeep.app) (formerly Hoarder) is a self-hosted bookmarking and read-it-later app with AI-assisted tagging. It saves links, snapshots webpage content, and uses a headless Chrome browser for full-page rendering. Search is powered by Meilisearch.

This composition runs three services: the main Karakeep application, a headless Chromium browser (`alpine-chrome`) for page snapshots, and Meilisearch for full-text search indexing.

## Ports

Internal port `3000`, bound to `127.0.0.1:8714`. Exposed via Traefik at `karakeep.<domain>`.

## Environment

Key environment variables (set in `.environment_vars`):

- `MEILI_ADDR` — set to `http://meilisearch:7700` (internal service)
- `BROWSER_WEB_URL` — set to `http://chrome:9222` (internal headless browser)
- `DATA_DIR` — `/data`

AI tagging via OpenAI is supported but not enabled by default (`OPENAI_API_KEY` is commented out).

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/karakeep` | Application data |
| `{{ composition_config }}/meilisearch` | Meilisearch index data |

## DNS

Registers subdomain: `karakeep`
