# MCP YouTube Transcript

Deploys [mcp-youtube-transcript](https://github.com/jkawamoto/mcp-youtube-transcript), a Model Context Protocol (MCP) server that fetches transcripts from YouTube videos. MCP-compatible LLM clients (for example, Claude Desktop, Open WebUI) can use it to retrieve video transcripts as context.

The role clones the source from GitHub and builds the image locally. The container runs with `stdin_open: true` and `tty: true`, because MCP servers communicate over stdio by default. The composition exposes no HTTP port. Clients connect over the Docker network, with the stdio transport.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/src` | Cloned source repository (used for build) |

## Notes

- No DNS subdomain is registered. This service is not for browser access.
- For SSE or network transport, you need additional configuration.
