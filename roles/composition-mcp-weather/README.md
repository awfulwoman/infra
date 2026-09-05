# composition-mcp-weather

Weather MCP server (https://github.com/weather-mcp/weather-mcp) — 17 weather
tools (forecasts, alerts, air quality, marine, radar, lightning, rivers,
wildfires, historical data back to 1940) backed entirely by free public APIs
(NOAA, Open-Meteo). No API keys required.

Upstream only speaks MCP over stdio, so this composition wraps it with
[mcp-proxy](https://github.com/sparfenyuk/mcp-proxy), which spawns
`npx -y @dangahagan/weather-mcp` and re-exposes it as Streamable HTTP on
`/mcp`. No auth is configured. The role gives the container no secrets to
guard, and Traefik scopes access to the Tailscale network.

## Adding to Claude Code

```bash
claude mcp add --transport http --scope user weather https://weathermcp.{{ domainname_infra }}/mcp
```

## Adding to Chives (nabu/jarvis)

Add to `composition_<name>_mcps` in the consuming role's defaults:

```yaml
composition_nabu_mcps:
  - url: "http://mcp-weather:8000/mcp" # on same host
```
