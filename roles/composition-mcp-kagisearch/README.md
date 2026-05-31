# composition-mcp-kagisearch

Kagi MCP server — exposes Kagi search and content extraction to MCP clients.

The server runs in HTTP mode. Each client supplies its own Kagi API key via
`Authorization: Bearer` header — no server-side key is stored.

## Adding to Claude Code

Get your API key from https://kagi.com/settings?p=api, then:

**Global** (all projects, stored in `~/.claude/`):
```bash
claude mcp add --transport http --scope user kagi https://kagimcp.{{ domainname_infra }}/mcp \
  --header "Authorization: Bearer <YOUR_KAGI_API_KEY>"
```

**Project** (shared with repo, stored in `.claude/`):
```bash
claude mcp add --transport http --scope project \
  --header "Authorization: Bearer <YOUR_KAGI_API_KEY>" \
  kagi https://kagimcp.{{ domainname_infra }}/mcp
```
