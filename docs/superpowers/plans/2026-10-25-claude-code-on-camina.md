# Claude Code on camina

> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move day-to-day Claude Code use from malcolm (Mac mini M4) to camina (control node). malcolm stays as the break-glass fallback and keeps the macOS-only services.

**Builds on:** Task 2 of `2026-08-30-ansible-vault-to-1password-connect.md`, which made camina the control node and put `system-claude` in its playbook.

## Already done

- [x] camina provisioned as control node (inventory, host_vars, host playbook)
- [x] `system-claude` in camina's playbook; Claude Code binary installed
- [x] `ansible-core`, `system-known-hosts`, `system-ssh-aliases` on camina
- [x] 1Password Connect moved to camina
- [x] Scheduled playbook runs moved to Semaphore on camina; `automation-infra` removed from malcolm
- [x] Fleet deploys verified from camina
- [x] Basic Memory on camina; AgentMemory vault synced via Syncthing

## State on 2026-10-25

- Claude Code 2.1.270 (stale, from 2026-09-14); config dir holds only `settings.json`
- No `CLAUDE.md`, rules, skills, memory or MCP config
- Only `/fastpool/repos/awfulwoman/infra` checked out, at `5ecd4d69` (stale)
- `gh` not logged in; `uv`, `node`, `op` missing
- No Ansible vault password file
- `fastpool` is now a 28G USB stick
- 7.6G RAM, ~6.3G available

## Task 1: Repos

- [ ] **Step 1: Decide location** — `~/Code/awfulwoman` (matches malcolm, keeps project memory paths) or `/fastpool/repos/awfulwoman` (snapshotted, `critical` policy). A symlink from one to the other gives both.
- [ ] **Step 2: Check capacity** — sum repo sizes on malcolm against 28G `fastpool`
- [ ] **Step 3: Declare checkouts in Ansible** — every repo in the top-level `CLAUDE.md` list, not hand-cloned
- [ ] **Step 4: Bring the infra checkout up to date**

## Task 2: Tooling

- [ ] **Step 1: Install `uv`** via Ansible
- [ ] **Step 2: Install `node`** if any MCP server or skill needs it
- [ ] **Step 3: Install `op` CLI** if wanted alongside Connect
- [ ] **Step 4: Update Claude Code** and confirm auto-update works under `CLAUDE_CONFIG_DIR`

## Task 3: Agent config

- [ ] **Step 1: Run `agents/install.py`** — links `CLAUDE.md`, rules, skills
- [ ] **Step 2: Check skills for macOS-only assumptions** (e.g. `awfulwoman-flush-dns`); skip or adapt
- [ ] **Step 3: Configure plugins** (basic-memory etc.)

## Task 4: MCP servers

- [ ] **Step 1: gateway** — confirm reachable from camina
- [ ] **Step 2: basic-memory** — point at the local server
- [ ] **Step 3: homeassistant, n8n, aw-deploy**
- [ ] **Step 4: claude.ai connectors** (Calendar, Context7, Docs) — come with the login

## Task 5: Credentials

- [ ] **Step 1: `claude` login**
- [ ] **Step 2: `gh auth login`**
- [ ] **Step 3: Ansible vault password** — copy out of band, or source from Connect
- [ ] **Step 4: SSH key** — confirm camina's key is authorised on every host and on GitHub

## Task 6: Memory

- [ ] **Step 1: Copy auto-memory** — `~/.config/claude/projects/<project>/memory/` from malcolm; directory names change if the repo path changes
- [ ] **Step 2: Update `sessions-run-on-malcolm` memory** to say camina
- [ ] **Step 3: Decide on old transcripts** — copy or leave on malcolm

## Task 7: Connect to loopback

- [ ] **Step 1: Do Step 4 of Task 2 in the 1Password plan** once Ansible runs from camina by default

## Task 8: Cutover

- [ ] **Step 1: Run a normal session on camina** — a commit, a playbook dry-run, a gateway call
- [ ] **Step 2: Make camina the default** — terminal / remote-control entry point
- [ ] **Step 3: Keep malcolm as break-glass** — decide how its infra checkout and vault password stay current

## Stays on malcolm

- `apple-calendar-server`, `apple-contacts-server`, `apple-reminders-server` (need macOS); camina reaches them via gateway
- Desktop Obsidian bridging Syncthing to Obsidian Sync
- Ollama
