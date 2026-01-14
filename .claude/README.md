# Claude Code Configuration

Project-specific configuration for [Claude Code](https://claude.ai/code).

This directory extends the project instructions in `CLAUDE.md` at the repository root. Rules here are automatically loaded alongside that file.

## Structure

| Directory/File | Description |
|----------------|-------------|
| `agents/` | Custom agent definitions |
| `commands/` | Custom slash commands |
| `rules/` | Project rules automatically loaded into context |
| `settings.local.json` | Local settings (gitignored) |

## Agents

Invoke agents by typing `@"agent-name (agent)"` in a message.

| Agent | Description |
|-------|-------------|
| **session-logger** | Documents work sessions to `worklog/` for continuity across sessions |
| **content-gap-reviewer** | Identifies missing content in documentation or configuration |

## Commands

Invoke commands by typing `/command-name` in a message.

| Command | Description |
|---------|-------------|
| `/commit` | Analyse changes, draft a commit message following conventional commits format, stage files, and commit |

## Rules

Rules in `rules/` are automatically included in Claude's context alongside `CLAUDE.md`:

| Rule | Description |
|------|-------------|
| **editorconfig.md** | Honour `.editorconfig` formatting |
| **precommit.md** | Run pre-commit hooks before committing |
| **python.md** | Use virtual environments for Python |
