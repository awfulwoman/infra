# Agent configuration

Project-scoped configuration for coding agents working in this repository.
Canonical location is `.opencode/`; `.claude` is a symlink to it, kept only
until Claude Code is dropped (planned for December 2026). Add files under
`.opencode/` and they appear at both paths.

## Structure

| Directory/File | Description |
|----------------|-------------|
| `rules/` | Project rules. OpenCode loads them through `instructions` in `opencode.jsonc`; Claude Code loads them automatically |
| `skills/` | Project-scoped skills, each in its own `<name>/SKILL.md` subdirectory. OpenCode discovers `.opencode/skills/` itself |
| `opencode.jsonc` | Project OpenCode configuration |
| `settings.json` | Claude Code settings, checked into the repo. OpenCode does not read it |

`.gitignore` here covers `settings.local.json`, which is per-machine.

## Skills

OpenCode advertises a skill when its `description` matches the task, and the
agent loads it with the `skill` tool. To load one yourself, mention it as
`@<skill-id>`; the ID comes from the directory name.

| Skill | Description |
|-------|-------------|
| `ansible-deploy` | Deploy Ansible playbooks through Semaphore, and select the right playbook and tags |
| `infra-health` | Check that infra hosts are reachable, that compositions run and stay healthy, and find cnames in host_vars with no matching composition |

Creating a new `composition-*` role is covered by the user-level
`awfulwoman-ansible-create-composition` skill in the `agents` repo.

## Rules

OpenCode has no rules directory of its own, so `opencode.jsonc` declares
`instructions: [".opencode/rules/*.md"]`. Add a rule here and it loads in
OpenCode and Claude Code alike.

| Rule | Description |
|------|-------------|
| `ansible-facts.md` | Access Ansible facts through the `ansible_facts` dict, not top-level `ansible_*` variables |
| `ansible-vault.md` | Generate secrets inline with `openssl rand -hex 32` when you vault them, not with a placeholder |
| `docker-healthcheck.md` | Use a shell TCP probe for Docker healthchecks, not `wget`/`curl`, unless the image confirms support |
| `precommit.md` | Install and run `pre-commit` before every commit |
| `python.md` | No virtual environment is necessary for this project. `ansible` and `pre-commit` come from Homebrew |

## Instructions

`AGENTS.md` at the repository root is the project instruction file. `CLAUDE.md`
is a symlink to it, so the two cannot drift. OpenCode reads `AGENTS.md` only.
