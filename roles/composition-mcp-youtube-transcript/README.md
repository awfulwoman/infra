# MCP YouTube Transcript

Deploys [mcp-youtube-transcript](https://github.com/jkawamoto/mcp-youtube-transcript), a Model Context Protocol (MCP) server that fetches transcripts from YouTube videos. This allows MCP-compatible LLM clients (e.g., Claude Desktop, Open WebUI) to retrieve video transcripts as context.

The source is cloned from GitHub and the image is built locally. The container runs with `stdin_open: true` and `tty: true` because MCP servers communicate over stdio by default. No HTTP port is exposed — clients connect via the Docker network using the stdio transport.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/src` | Cloned source repository (used for build) |

## Notes

- No DNS subdomain is registered; this service is not intended for browser access.
- For SSE/network transport, additional configuration would be needed.
