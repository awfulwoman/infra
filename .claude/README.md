# Claude Code Configuration

Project-specific configuration for [Claude Code](https://claude.ai/code).

## Structure

| Directory/File | Description |
|----------------|-------------|
| `agents/` | Custom agent definitions (session-logger, content-gap-reviewer) |
| `commands/` | Custom slash commands (e.g., `/commit`) |
| `rules/` | Project rules automatically loaded into context |
| `settings.local.json` | Local settings (gitignored) |

## Agents

- **session-logger** — Documents work sessions to `worklog/` for continuity
- **content-gap-reviewer** — Identifies missing content in documentation

## Rules

Rules in `rules/` are automatically included in Claude's context:

- **editorconfig.md** — Honour `.editorconfig` formatting
- **precommit.md** — Run pre-commit hooks before committing
- **python.md** — Use virtual environments for Python
