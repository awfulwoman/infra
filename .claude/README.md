# Claude Code Configuration

This directory extends the project instructions in `CLAUDE.md`, at the
repository root. Claude Code loads the rules here alongside that file.

## Structure

| Directory/File | Description |
|----------------|-------------|
| `rules/` | Project rules, loaded into context automatically |
| `skills/` | Project-scoped skills, each in its own `<name>/SKILL.md` subdirectory |
| `settings.json` | Shared settings, checked into the repo |
| `settings.local.json` | Local settings (gitignored) |

## Skills

To invoke a skill, type `/skill-name` in a message. Each skill lives in its
own subdirectory: `skills/<name>/SKILL.md`.

| Skill | Description |
|-------|-------------|
| `ansible-deploy` | Deploy Ansible playbooks to hosts or groups, and select the right playbook and tags |
| `create-composition` | Create a new Docker Compose-based Ansible role (`composition-*`), from a GitHub repo or install docs |
| `infra-health` | Check that infra hosts are reachable, that compositions run and stay healthy, and find cnames in host_vars with no matching composition |

## Rules

Claude Code loads rules in `rules/` into context automatically, alongside
`CLAUDE.md`.

| Rule | Description |
|------|-------------|
| `ansible-facts.md` | Access Ansible facts through the `ansible_facts` dict, not top-level `ansible_*` variables |
| `ansible-vault.md` | Generate secrets inline with `openssl rand -hex 32` when you vault them, not with a placeholder |
| `docker-healthcheck.md` | Use a shell TCP probe for Docker healthchecks, not `wget`/`curl`, unless the image confirms support |
| `precommit.md` | Install and run `pre-commit` before every commit |
| `python.md` | No virtual environment is necessary for this project. `ansible` and `pre-commit` come from Homebrew |
