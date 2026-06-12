# `aw-deploy`: A localhost playbook-runner service for agents

Date: 2026-06-12
Status: Design (pending review)

## Goal

Let an agent (or shell script) running on host X invoke an Ansible playbook from
this repo against any inventory host, without leaving its current working
directory. The agent calls a local MCP tool; deploy execution happens from the
same machine that received the request, using that machine's already-configured
ansible setup (vault password, SSH keys, infra checkout).

Primary callers:

- Claude Code agents working in other repos (e.g. `personal-site`).
- Generic shell scripts (cron jobs, ad-hoc commands).

Primary hosts where the service runs:

- The user's laptop.
- Malcolm (Apple Mac Mini M4 16GB, always-on macOS host).

Both hosts already have this repo cloned at `~/Code/awfulwoman/infra` and a
working `ansible` install with the `beanpod` vault identity configured.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Host (laptop OR Malcolm)                                       │
│                                                                 │
│  Claude Code agent ─stdio MCP──▶ aw-deploy-mcp ──exec─▶ ┐       │
│                                                         │       │
│  Shell script ─────────────────▶ aw-deploy ─────────────┤       │
│                                                         │       │
│                                                         ▼       │
│                                              ansible-playbook   │
│                                                         │       │
│                                                         ▼       │
│                                              ~/Code/awfulwoman/ │
│                                                infra (checkout) │
│                                                         │       │
└─────────────────────────────────────────────────────────┼───────┘
                                                          │ SSH
                                                          ▼
                                                   target host(s)
```

Three artefacts on each host:

| Artefact | Where it lives | Owned by |
|---|---|---|
| `aw-deploy` CLI | `/usr/local/bin/aw-deploy` | Ansible role `system-aw-deploy` |
| `aw-deploy-mcp` shim | `/usr/local/bin/aw-deploy-mcp` | Ansible role `system-aw-deploy` |
| MCP server registration in `~/.claude.json` | top-level `mcpServers.aw-deploy` | chezmoi `modify_dot_claude.json.tmpl` |

Ownership boundary: **Ansible installs binaries; chezmoi merges Claude Code
config; neither writes to the other's domain.**

## Components

### 1. `aw-deploy` CLI

The canonical, dumb entry point. A Python script (~150 LOC) that wraps
`ansible-playbook`.

**Commands:**

```
aw-deploy run <playbook> [--limit HOST] [--tags T1,T2] [--extra-vars k=v ...] [--check]
aw-deploy list                    # list playbooks under playbooks/
aw-deploy hosts                   # list inventory hosts and groups
aw-deploy logs [--tail N]         # show last N runs' logs
```

**Behaviour:**

- Resolves the infra repo via `AW_INFRA_DIR` (default `~/Code/awfulwoman/infra`).
  `cd`s into that directory before invoking `ansible-playbook` so that the
  existing `ansible.cfg` and inventory paths resolve correctly.
- Streams `ansible-playbook` stdout/stderr unmodified to the caller's terminal.
- Holds an exclusive `flock` on `~/.local/state/aw-deploy/run.lock` for the
  duration of the run. A second invocation fails fast with a clear error rather
  than queueing.
- Writes a copy of each run's output to
  `~/.local/state/aw-deploy/runs/<YYYYMMDDTHHMMSS>-<playbook-slug>.log` (UTC,
  filesystem-safe — no colons). Keeps the most recent 30 runs, prunes older.

**Exit codes:**

- 0 — ansible-playbook exited 0.
- non-zero — passes through ansible's exit code.
- 64 — locked: another run is in progress.
- 65 — bad arguments / playbook not found.

### 2. `aw-deploy-mcp` shim

A paper-thin stdio MCP server (Python, using the `mcp` SDK; ~100 LOC). Spawned
per-session by Claude Code. Each tool shells out to `aw-deploy` and streams the
output back.

**Tools exposed:**

| Tool | Maps to |
|---|---|
| `run_playbook(playbook, limit?, tags?, extra_vars?, check?)` | `aw-deploy run …` |
| `list_playbooks()` | `aw-deploy list` |
| `list_hosts()` | `aw-deploy hosts` |
| `last_run(playbook?)` | reads last log under `~/.local/state/aw-deploy/runs/` |

The shim has no business logic; everything goes through the CLI.

### 3. Ansible role `system-aw-deploy`

A new `system-*` role (no Docker, matches `system-mcp-gateway`'s native pattern).

**Tasks:**

1. Ensure `uv` (or `pipx`) is available — used to manage the MCP SDK venv.
2. Create venv at `/opt/aw-deploy/venv` (Linux) or
   `~/Library/Application Support/aw-deploy/venv` (macOS); install `mcp` SDK.
3. Render and install:
   - `scripts/aw-deploy` → `/usr/local/bin/aw-deploy`
   - `scripts/aw-deploy-mcp` → `/usr/local/bin/aw-deploy-mcp`
4. Both scripts have shebangs pointing at the venv's `python`.
5. No edits to Claude Code config — that's chezmoi's job.

**Defaults:**

```yaml
ansible_mcp_install_prefix: /usr/local/bin
ansible_mcp_state_dir: "{{ ansible_facts['user_dir'] }}/.local/state/aw-deploy"
ansible_mcp_infra_dir: "{{ ansible_facts['user_dir'] }}/Code/awfulwoman/infra"
```

**Applied to:**

- `inventory/host_vars/<laptop>/core.yaml` — add `system-aw-deploy` to roles.
- `inventory/host_vars/apple-macmini-m4-16gb-malcolm/core.yaml` — same.

### 4. Chezmoi `modify_dot_claude.json.tmpl`

A new script in the chezmoi source state (this lives in the user's dotfiles
repo, NOT in this infra repo). Executable. Receives current `~/.claude.json` on
stdin, outputs the merged JSON on stdout.

**Logic:**

1. Parse stdin as JSON. If invalid, write the input back unchanged and exit
   non-zero (fail loudly rather than corrupt the file).
2. Ensure `data["mcpServers"]` is a dict (create if missing).
3. If `/usr/local/bin/aw-deploy-mcp` exists on this host:
   - Set `data["mcpServers"]["aw-deploy"]` to:
     ```json
     {
       "type": "stdio",
       "command": "/usr/local/bin/aw-deploy-mcp"
     }
     ```
4. If `/usr/local/bin/aw-deploy-mcp` does NOT exist:
   - Remove `data["mcpServers"]["aw-deploy"]` if present.
5. Write `data` to stdout as JSON, preserving key order and the file's existing
   indentation style.

The presence-of-binary check is what makes this work on every machine: the
script is the same in the dotfiles repo, but only hosts where Ansible has
installed `aw-deploy-mcp` end up with the registration.

## Data flow: a Claude Code agent in `personal-site` deploys

```
1. User in personal-site session: "deploy this to public01"
2. Agent calls MCP tool: aw-deploy.run_playbook(
       playbook="playbooks/groups/web/deploy-personal-site.yaml",
       limit="public01"
   )
3. Claude Code spawns: /usr/local/bin/aw-deploy-mcp (stdio MCP server)
4. Shim execs: aw-deploy run playbooks/.../deploy-personal-site.yaml --limit public01
5. aw-deploy: acquires flock, cds to ~/Code/awfulwoman/infra,
   runs `ansible-playbook --limit public01 playbooks/.../deploy-personal-site.yaml`
6. ansible-playbook: uses the host's existing vault password file and SSH keys
   to deploy to public01.
7. Output streams: ansible → aw-deploy → MCP shim → Claude Code session.
8. Log written to ~/.local/state/aw-deploy/runs/20260612T142300-deploy-personal-site.log
```

## Locked-in decisions

| Decision | Choice |
|---|---|
| Transport | MCP stdio (server spawned per Claude Code session) |
| Service deployment | None — no daemon, no launchd, no Docker |
| Install location | `/usr/local/bin/aw-deploy` and `/usr/local/bin/aw-deploy-mcp` |
| Repo dir resolution | `AW_INFRA_DIR` env var; default `~/Code/awfulwoman/infra` |
| Vault password | Use host's already-configured vault password file |
| MCP registration | chezmoi `modify_` script keyed off binary presence |
| Concurrency | Single global `flock` on `~/.local/state/aw-deploy/run.lock` |
| Logs | `~/.local/state/aw-deploy/runs/`, 30-run rolling retention |
| Auth | None (localhost-only, no network surface) |

## Out of scope

- Cross-host triggering (e.g. agent on laptop triggering deploy *from* Malcolm).
  Each agent uses the host it's running on.
- Web UI, job dashboard.
- Per-playbook auth / RBAC.
- Async / background runs. All runs are synchronous; output streams in real time.
- Auto-update of the infra repo before each run. The CLI uses whatever is
  checked out; keeping the repo current is the user's responsibility (could
  later be a `--pull` flag or a chezmoi-managed cron).

## Open questions

1. **Should `aw-deploy run` `git pull` first?** Decision deferred to
   implementation: probably no by default, with `--pull` flag, but reconsider
   if confused-deploy-state happens in practice.
2. **macOS install prefix**: `/usr/local/bin/` works but on Apple Silicon the
   conventional Homebrew prefix is `/opt/homebrew/bin/`. Either is fine for our
   scripts (we're not using Homebrew); `/usr/local/bin/` is consistent across
   Intel and Apple Silicon Macs and Linux. Sticking with `/usr/local/bin/`.
3. **MCP shim Python deps**: `mcp` SDK only, no other runtime deps. Decision:
   isolated venv at a known path; scripts shebang into it.

## Implementation footprint estimate

- New role `roles/system-aw-deploy/`: ~80 lines of YAML + 2 script templates.
- `scripts/aw-deploy`: ~150 lines Python.
- `scripts/aw-deploy-mcp`: ~100 lines Python.
- chezmoi `modify_dot_claude.json.tmpl`: ~40 lines Python (lives in dotfiles
  repo, not this repo).
- Host config additions: 1 line each in two `host_vars/<host>/core.yaml` files.
- Total: ~370 LOC across two repos.
