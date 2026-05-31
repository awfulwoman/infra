# composition-kagimcp

Kagi MCP server — exposes Kagi search and content extraction to MCP clients.

## Adding to Claude Code

**Global** (all projects, stored in `~/.claude/`):
```bash
claude mcp add --transport http --scope user kagi https://kagimcp.{{ domainname_infra }}/mcp
```

**Project** (shared with repo, stored in `.claude/`):
```bash
claude mcp add --transport http --scope project kagi https://kagimcp.{{ domainname_infra }}/mcp
```
