# Basic Memory

This role deploys [Basic Memory](https://github.com/basicmachines-co/basic-memory),
an MCP server that gives agents a shared, persistent memory. Memory is stored
as plain markdown with wikilinks. On top of it, Basic Memory keeps a full-text,
semantic and knowledge-graph index.

It serves one project, `agentmemory`, rooted at the synced **Obsidian:
AgentMemory** Syncthing folder. Everything an agent writes also reaches
storage (backed up), agatha and malcolm, and gets to the phone through
Obsidian Sync.

## Endpoint

`https://basic-memory.<domainname_infra>/mcp` uses the streamable HTTP
transport.

Basic Memory has no authentication of its own. Traefik puts basic auth in
front of it: user `agents`, password `vault_basic_memory_password`. MCP
clients send the credentials as a header:

```
Authorization: Basic <base64 of agents:PASSWORD>
```

## Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_basic_memory_vault_path` | *(required)* | Host path of the notes (the AgentMemory Syncthing folder) |
| `composition_basic_memory_project` | `agentmemory` | Project name; the server is restricted to it |
| `composition_basic_memory_image` | `ghcr.io/basicmachines-co/basic-memory:<tag>` | Pinned. The tags have no `v` prefix |
| `composition_basic_memory_htpasswd` | `vault_basic_memory_htpasswd` | bcrypt htpasswd line for Traefik |

## Volumes

| Host | Container | Purpose |
|---|---|---|
| `composition_basic_memory_vault_path` | `/app/data` | The notes |
| `{{ composition_config }}/state` | `/home/appuser/.basic-memory` | Config, SQLite index. You can rebuild it from the notes |
| `{{ composition_config }}/cache` | `/home/appuser/.cache` | Embedding model for semantic search |

## Behaviour to know

- On first indexing, Basic Memory adds `title`, `type` and `permalink`
  frontmatter to every note that lacks it. Those edits sync everywhere.
- `config.json` is seeded once and then left to Basic Memory, which rewrites
  it.
- Auto-update is disabled. Upgrade by bumping the image tag.
