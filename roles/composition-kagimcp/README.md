# composition-kagimcp

Kagi MCP server — exposes Kagi search and content extraction to MCP clients.

## Adding to Claude Code

**Global** (all projects):
```bash
claude mcp add --transport http kagi https://kagimcp.{{ domainname_infra }}/mcp
```

**Project** (current repo only):
```bash
claude mcp add --transport http --scope project kagi https://kagimcp.{{ domainname_infra }}/mcp
```
