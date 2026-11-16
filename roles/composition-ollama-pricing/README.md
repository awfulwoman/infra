# composition-ollama-pricing

Runs [ollama-pricing](https://github.com/awfulwoman/ollama-pricing) at
`https://ollama-pricing.{{ domainname_infra }}`.

Ollama's API publishes no prices, so the service scrapes ollama.com's cloud
catalogue once a day and serves it in opencode's model shape:

- `GET /v1/opencode` — `providers.ollama.models` entries with `name` (including
  ollama.com's `$` … `$$$$` usage tier) and `cost` (USD per million tokens).
- `GET /v1/models` — the raw catalogue: prices, peak/off-peak, context, size.
- `GET /healthz` — model count and the last scrape result.

`system-opencode` installs a plugin that reads `/v1/opencode` at startup and
refreshes it daily, so the model list stays discovery-driven and this role never
holds one.

## Variables

See `defaults/main.yaml`:

- `composition_ollama_pricing_image`: `ghcr.io/awfulwoman/ollama-pricing:latest`
- `composition_ollama_pricing_refresh_seconds`: scrape interval, default daily
- `composition_ollama_pricing_hostname`: `ollama-pricing.<domain>`

## Notes

- No secrets. Prices are public, so the route has no token.
- The last good scrape is persisted in `{{ composition_config }}/data`, so a
  restart before the first scrape still serves prices. A failed scrape keeps the
  previous catalogue and reports the error from `/healthz`.
- The scraper depends on ollama.com's HTML. It reads the cloud listing (for the
  `$` tier) and each `:cloud` tag page (for the price). A redesign of those
  pages fails the scrape, not the service: the previous data stays in place.
