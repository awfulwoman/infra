# Claude Code Configuration

Project-specific configuration for [Claude Code](https://claude.ai/code).

This directory extends the project instructions in `CLAUDE.md` at the repository root. Rules here are automatically loaded alongside that file.

## Structure

| Directory/File | Description |
|----------------|-------------|
| `agents/` | Custom agent definitions |
| `commands/` | Custom slash commands |
| `rules/` | Project rules automatically loaded into context |
| `skills/` | Project-scoped skills (each in its own `<name>/SKILL.md` subdirectory) |
| `settings.local.json` | Local settings (gitignored) |

## Agents

Invoke agents by typing `@"agent-name (agent)"` in a message.

| Agent | Description |
|-------|-------------|
| **content-gap-reviewer** | Identifies missing content in documentation or configuration |

## Commands

Invoke commands by typing `/command-name` in a message.

| Command | Description |
|---------|-------------|
| `/commit` | Analyse changes, draft a commit message following conventional commits format, stage files, and commit |
| `/log` | Document the current work session to `worklog/` for continuity across sessions |

## Skills

Invoke skills by typing `/skill-name` in a message. Each skill lives in its own subdirectory: `skills/<name>/SKILL.md`.

| Skill | Description |
|-------|-------------|
| `ansible-deploy` | Deploy Ansible playbooks to hosts or groups, selecting the right playbook and tags |
| `create-composition` | Create a new Docker Compose-based Ansible role (`composition-*`) from a GitHub repo or install docs |

## Rules

Rules in `rules/` are automatically included in Claude's context alongside `CLAUDE.md`:

| Rule | Description |
|------|-------------|
| **editorconfig.md** | Honour `.editorconfig` formatting |
| **precommit.md** | Run pre-commit hooks before committing |
| **python.md** | Use virtual environments for Python |
