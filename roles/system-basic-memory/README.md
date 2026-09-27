# system-basic-memory

This role installs the [Basic Memory](https://github.com/basicmachines-co/basic-memory)
CLI (`bm`) natively on macOS. It registers the synced AgentMemory folder as the
default project.

On malcolm, Claude Code uses it in two ways. Its `basic-memory` MCP server runs
`bm mcp` locally over stdio. The Basic Memory Claude Code plugin's hooks
(session-start briefing, pre-compaction checkpoint) run `bm` against the same
local project. The notes reach every other agent through Syncthing, including
`composition-basic-memory` on camina and Hermes-Jarvis on agatha.

## What it does

- Installs `bm` with `uv tool install` at a pinned version, with `sqlite-vec`
  pinned too (see defaults). It reinstalls only when the pins change.
- Turns off bm's self-update (`auto_update=false`).
- Registers `system_basic_memory_project` at `system_basic_memory_project_path`
  and makes it the default.

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_basic_memory_project_path` | *(required)* | Local path of the notes (the AgentMemory Syncthing folder) |
| `system_basic_memory_project` | `agentmemory` | Project name |
| `system_basic_memory_version` | `0.23.2` | Keep in step with camina and Jarvis |
| `system_basic_memory_sqlite_vec_version` | `0.1.9` | From basic-memory's lockfile |

Claude Code's side (the plugin install, the MCP entry, the `BM_BIN` env) is
set with the `claude` CLI; see the agents repo's AGENTS.md ("Wire up MCP servers and shared memory").
