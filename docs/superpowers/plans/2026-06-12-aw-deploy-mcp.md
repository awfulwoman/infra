# aw-deploy MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a localhost CLI (`aw-deploy`) and MCP shim (`aw-deploy-mcp`) that lets agents in any project trigger Ansible playbook runs from the local infra repo checkout, with an Ansible role that installs both on Malcolm and a chezmoi modify script that registers the MCP server in `~/.claude.json` on any machine where the binary is present.

**Architecture:** The `aw-deploy` CLI wraps `ansible-playbook`, running from `~/Code/awfulwoman/infra` using the host's existing vault/SSH config. `aw-deploy-mcp` is a paper-thin stdio MCP server (using the `mcp` Python SDK in an isolated venv) that shells out to the CLI. The chezmoi `modify_dot_claude.json` script merges the MCP registration into `~/.claude.json` on any host where the binary exists — so Ansible installs the binaries and chezmoi handles the Claude Code config, with no cross-tool file conflicts.

**Tech Stack:** Python 3 (stdlib only for CLI; `mcp` SDK for shim), Ansible, uv (venv management on macOS), chezmoi modify scripts.

---

## File Map

**Created in this repo (`infra`):**
- `roles/system-aw-deploy/defaults/main.yaml` — role variable defaults
- `roles/system-aw-deploy/tasks/main.yaml` — macOS install tasks
- `roles/system-aw-deploy/files/aw-deploy` — CLI script (stdlib only)
- `roles/system-aw-deploy/templates/aw-deploy-mcp.j2` — MCP shim (rendered shebang)
- `roles/system-aw-deploy/README.md` — role documentation

**Modified in this repo:**
- `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml` — add `system-aw-deploy` role

**Created in dotfiles repo (`~/.local/share/chezmoi`):**
- `modify_dot_claude.json` — chezmoi modify script (executable Python)

---

## Task 1: Create the `aw-deploy` CLI script

**Files:**
- Create: `roles/system-aw-deploy/files/aw-deploy`

- [ ] **Step 1: Create the role directory structure**

```bash
mkdir -p /Users/charlie/Code/awfulwoman/infra/roles/system-aw-deploy/{defaults,tasks,files,templates}
```

- [ ] **Step 2: Write the CLI script**

Create `roles/system-aw-deploy/files/aw-deploy` with this exact content:

```python
#!/usr/bin/env python3
"""Run Ansible playbooks from the infra repo."""
import argparse
import fcntl
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

INFRA_DIR = Path(os.environ.get("AW_INFRA_DIR", Path.home() / "Code/awfulwoman/infra"))
STATE_DIR = Path(os.environ.get("AW_STATE_DIR", Path.home() / ".local/state/aw-deploy"))
RUNS_DIR = STATE_DIR / "runs"
LOCK_FILE = STATE_DIR / "run.lock"
MAX_RUNS = 30


def _ensure_dirs():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _prune_runs():
    runs = sorted(RUNS_DIR.glob("*.log"))
    for old in runs[:-MAX_RUNS]:
        old.unlink()


def cmd_run(args):
    playbook_path = INFRA_DIR / args.playbook
    if not playbook_path.exists():
        print(f"error: playbook not found: {playbook_path}", file=sys.stderr)
        sys.exit(65)

    cmd = ["ansible-playbook", str(playbook_path)]
    if args.limit:
        cmd += ["--limit", args.limit]
    if args.tags:
        cmd += ["--tags", args.tags]
    for kv in args.extra_vars or []:
        cmd += ["--extra-vars", kv]
    if args.check:
        cmd += ["--check"]

    _ensure_dirs()

    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("error: another aw-deploy run is in progress", file=sys.stderr)
        sys.exit(64)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    slug = args.playbook.replace("/", "-").replace(".yaml", "")
    log_path = RUNS_DIR / f"{ts}-{slug}.log"

    try:
        with open(log_path, "w") as log_fh:
            proc = subprocess.Popen(
                cmd,
                cwd=str(INFRA_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            for line in proc.stdout:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
                log_fh.buffer.write(line)
            proc.wait()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

    _prune_runs()
    sys.exit(proc.returncode)


def cmd_list(args):
    playbooks_dir = INFRA_DIR / "playbooks"
    if not playbooks_dir.exists():
        print(f"error: playbooks dir not found: {playbooks_dir}", file=sys.stderr)
        sys.exit(65)
    for p in sorted(playbooks_dir.rglob("*.yaml")):
        print(str(p.relative_to(INFRA_DIR)))


def cmd_hosts(args):
    result = subprocess.run(
        ["ansible-inventory", "--graph"],
        cwd=str(INFRA_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(result.stdout)


def cmd_logs(args):
    _ensure_dirs()
    runs = sorted(RUNS_DIR.glob("*.log"))
    for log in runs[-(args.tail or 5):]:
        print(f"\n=== {log.name} ===")
        print(log.read_text())


def main():
    parser = argparse.ArgumentParser(description="Run Ansible playbooks from the infra repo")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a playbook")
    p_run.add_argument("playbook", help="Path relative to infra repo root, e.g. playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml")
    p_run.add_argument("--limit", help="Limit to a specific host or group")
    p_run.add_argument("--tags", help="Comma-separated Ansible tags")
    p_run.add_argument("--extra-vars", action="append", metavar="KEY=VALUE")
    p_run.add_argument("--check", action="store_true", help="Dry run (passes --check to ansible-playbook)")
    p_run.set_defaults(func=cmd_run)

    p_list = sub.add_parser("list", help="List available playbooks")
    p_list.set_defaults(func=cmd_list)

    p_hosts = sub.add_parser("hosts", help="List inventory hosts and groups")
    p_hosts.set_defaults(func=cmd_hosts)

    p_logs = sub.add_parser("logs", help="Show recent run logs")
    p_logs.add_argument("--tail", type=int, default=5, metavar="N", help="Number of recent runs to show (default: 5)")
    p_logs.set_defaults(func=cmd_logs)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Make the file executable**

```bash
chmod +x /Users/charlie/Code/awfulwoman/infra/roles/system-aw-deploy/files/aw-deploy
```

- [ ] **Step 4: Smoke-test the CLI locally**

Copy to a temp location and verify it parses args and finds playbooks:

```bash
cp /Users/charlie/Code/awfulwoman/infra/roles/system-aw-deploy/files/aw-deploy /tmp/aw-deploy
chmod +x /tmp/aw-deploy
/tmp/aw-deploy --help
/tmp/aw-deploy list | head -10
```

Expected: `--help` prints usage; `list` outputs playbook paths like `playbooks/hosts/.../core.yaml`.

- [ ] **Step 5: Commit**

```bash
cd /Users/charlie/Code/awfulwoman/infra
git add roles/system-aw-deploy/files/aw-deploy
git commit -m "feat(system-aw-deploy): add aw-deploy CLI script"
```

---

## Task 2: Create the `aw-deploy-mcp` MCP shim template

**Files:**
- Create: `roles/system-aw-deploy/templates/aw-deploy-mcp.j2`

The shim is an Ansible template so that the venv path (a role variable) is rendered into the shebang line. The Python code itself is identical on every host.

- [ ] **Step 1: Write the template**

Create `roles/system-aw-deploy/templates/aw-deploy-mcp.j2`:

```jinja2
#!{{ system_aw_deploy_venv_dir }}/bin/python3
"""Stdio MCP server: thin wrapper around the aw-deploy CLI."""
import asyncio
import os
import subprocess
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

AW_DEPLOY = os.environ.get("AW_DEPLOY_BIN", "/usr/local/bin/aw-deploy")
STATE_DIR = Path(os.environ.get("AW_STATE_DIR", Path.home() / ".local/state/aw-deploy"))
RUNS_DIR = STATE_DIR / "runs"

server = Server("aw-deploy")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="run_playbook",
            description=(
                "Run an Ansible playbook from ~/Code/awfulwoman/infra. "
                "Streams output back. Use 'list_playbooks' first to see valid paths. "
                "Example playbook: 'playbooks/hosts/apple-macmini-m4-16gb-malcolm/compositions.yaml'"
            ),
            inputSchema={
                "type": "object",
                "required": ["playbook"],
                "properties": {
                    "playbook": {
                        "type": "string",
                        "description": "Playbook path relative to infra repo root",
                    },
                    "limit": {
                        "type": "string",
                        "description": "Limit to a specific Ansible host or group",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated Ansible tags to run",
                    },
                    "extra_vars": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Extra variables as KEY=VALUE strings",
                    },
                    "check": {
                        "type": "boolean",
                        "description": "Dry run: passes --check to ansible-playbook, no changes made",
                    },
                },
            },
        ),
        types.Tool(
            name="list_playbooks",
            description="List all available playbooks in the infra repo.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="list_hosts",
            description="List Ansible inventory hosts and groups.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="last_run",
            description="Show the log from the most recent aw-deploy run, optionally filtered by playbook name fragment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playbook": {
                        "type": "string",
                        "description": "Optional fragment to filter logs by playbook name",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "run_playbook":
        cmd = [AW_DEPLOY, "run", arguments["playbook"]]
        if arguments.get("limit"):
            cmd += ["--limit", arguments["limit"]]
        if arguments.get("tags"):
            cmd += ["--tags", arguments["tags"]]
        for ev in arguments.get("extra_vars") or []:
            cmd += ["--extra-vars", ev]
        if arguments.get("check"):
            cmd += ["--check"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            return [types.TextContent(type="text", text=f"FAILED (exit {result.returncode}):\n{output}")]
        return [types.TextContent(type="text", text=output)]

    if name == "list_playbooks":
        result = subprocess.run([AW_DEPLOY, "list"], capture_output=True, text=True)
        return [types.TextContent(type="text", text=result.stdout or result.stderr)]

    if name == "list_hosts":
        result = subprocess.run([AW_DEPLOY, "hosts"], capture_output=True, text=True)
        return [types.TextContent(type="text", text=result.stdout or result.stderr)]

    if name == "last_run":
        if not RUNS_DIR.exists():
            return [types.TextContent(type="text", text="No runs found.")]
        fragment = arguments.get("playbook", "")
        pattern = f"*{fragment}*.log" if fragment else "*.log"
        runs = sorted(RUNS_DIR.glob(pattern))
        if not runs:
            return [types.TextContent(type="text", text="No matching runs found.")]
        return [types.TextContent(type="text", text=f"{runs[-1].name}:\n\n{runs[-1].read_text()}")]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
cd /Users/charlie/Code/awfulwoman/infra
git add roles/system-aw-deploy/templates/aw-deploy-mcp.j2
git commit -m "feat(system-aw-deploy): add aw-deploy-mcp MCP shim template"
```

---

## Task 3: Create the `system-aw-deploy` Ansible role

**Files:**
- Create: `roles/system-aw-deploy/defaults/main.yaml`
- Create: `roles/system-aw-deploy/tasks/main.yaml`
- Create: `roles/system-aw-deploy/README.md`

- [ ] **Step 1: Write role defaults**

Create `roles/system-aw-deploy/defaults/main.yaml`:

```yaml
---
system_aw_deploy_install_dir: /usr/local/bin
system_aw_deploy_opt_dir: "{{ awfulwoman_opt_dir }}/aw-deploy"
system_aw_deploy_venv_dir: "{{ system_aw_deploy_opt_dir }}/venv"
system_aw_deploy_infra_dir: "{{ ansible_facts.user_dir }}/Code/awfulwoman/infra"
system_aw_deploy_state_dir: "{{ ansible_facts.user_dir }}/.local/state/aw-deploy"
```

- [ ] **Step 2: Write role tasks**

Create `roles/system-aw-deploy/tasks/main.yaml`:

```yaml
# code: language=ansible
---
- name: "Assert macOS"
  ansible.builtin.assert:
    that: ansible_facts['os_family'] == 'Darwin'
    fail_msg: "system-aw-deploy is macOS-only"

- name: "Ensure uv is installed"
  community.general.homebrew:
    name: uv
    state: present

- name: "Ensure opt directory exists"
  become: true
  ansible.builtin.file:
    path: "{{ system_aw_deploy_opt_dir }}"
    state: directory
    mode: "0755"
    owner: "{{ ansible_user }}"
    group: staff

- name: "Ensure state/runs directory exists"
  ansible.builtin.file:
    path: "{{ system_aw_deploy_state_dir }}/runs"
    state: directory
    mode: "0755"

- name: "Create Python venv"
  ansible.builtin.command:
    cmd: /opt/homebrew/bin/uv venv {{ system_aw_deploy_venv_dir }}
    creates: "{{ system_aw_deploy_venv_dir }}/bin/python3"

- name: "Install mcp package into venv"
  ansible.builtin.command:
    cmd: /opt/homebrew/bin/uv pip install mcp
  environment:
    VIRTUAL_ENV: "{{ system_aw_deploy_venv_dir }}"
  changed_when: false
  when: not ansible_check_mode

- name: "Install aw-deploy CLI"
  become: true
  ansible.builtin.copy:
    src: aw-deploy
    dest: "{{ system_aw_deploy_install_dir }}/aw-deploy"
    mode: "0755"
    owner: root
    group: wheel

- name: "Install aw-deploy-mcp shim"
  become: true
  ansible.builtin.template:
    src: aw-deploy-mcp.j2
    dest: "{{ system_aw_deploy_install_dir }}/aw-deploy-mcp"
    mode: "0755"
    owner: root
    group: wheel
```

- [ ] **Step 3: Write README**

Create `roles/system-aw-deploy/README.md`:

```markdown
# system-aw-deploy

Installs `aw-deploy` (CLI) and `aw-deploy-mcp` (stdio MCP server) so that agents
and scripts on this host can trigger Ansible playbook runs from the local infra
repo checkout.

## Requirements

- macOS only
- `uv` installed via Homebrew (this role installs it if absent)
- `~/Code/awfulwoman/infra` cloned with vault password configured

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_aw_deploy_install_dir` | `/usr/local/bin` | Where to install the binaries |
| `system_aw_deploy_opt_dir` | `{{ awfulwoman_opt_dir }}/aw-deploy` | Working dir for venv |
| `system_aw_deploy_venv_dir` | `{{ system_aw_deploy_opt_dir }}/venv` | Python venv path |
| `system_aw_deploy_infra_dir` | `~/Code/awfulwoman/infra` | Infra repo location |
| `system_aw_deploy_state_dir` | `~/.local/state/aw-deploy` | Run logs location |

## Usage

```bash
aw-deploy run playbooks/hosts/apple-macmini-m4-16gb-malcolm/compositions.yaml --tags homeassistant
aw-deploy run playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml --check
aw-deploy list
aw-deploy logs --tail 3
```

## MCP registration

The binary alone is not enough — Claude Code also needs the server registered in
`~/.claude.json`. This is handled by the chezmoi `modify_dot_claude.json` script in the
dotfiles repo, which detects the binary and merges the entry automatically on `chezmoi apply`.
```

- [ ] **Step 4: Commit**

```bash
cd /Users/charlie/Code/awfulwoman/infra
git add roles/system-aw-deploy/
git commit -m "feat: add system-aw-deploy Ansible role"
```

---

## Task 4: Add role to Malcolm and run playbook

**Files:**
- Modify: `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`

- [ ] **Step 1: Add the role to Malcolm's playbook**

In `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml`, add `system-aw-deploy` before the final `monitoring-healthchecksio` success ping. The existing final two entries are:

```yaml
  - role: system-agent-chives
    tags: [system, system-agent-chives]
  - role: monitoring-healthchecksio
    monitoring_healthchecksio_ping_type: success
    tags: [monitoring, monitoring-healthchecksio]
```

Insert after `system-agent-chives`:

```yaml
  - role: system-aw-deploy
    tags: [system, system-aw-deploy]
```

- [ ] **Step 2: Run in check mode against Malcolm**

```bash
cd /Users/charlie/Code/awfulwoman/infra
ansible-playbook playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml \
  --tags system-aw-deploy --check
```

Expected: tasks show as `ok` or `changed` with no errors. The `uv pip install` task will be skipped in check mode (that's expected — it has `when: not ansible_check_mode`).

- [ ] **Step 3: Run for real against Malcolm**

```bash
ansible-playbook playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml \
  --tags system-aw-deploy
```

Expected: venv created, `mcp` installed, both binaries in `/usr/local/bin/`.

- [ ] **Step 4: Verify on Malcolm**

```bash
ssh malcolm 'aw-deploy list | head -5'
ssh malcolm 'aw-deploy hosts | head -10'
```

Expected: playbook paths and inventory group tree are printed.

- [ ] **Step 5: Commit**

```bash
cd /Users/charlie/Code/awfulwoman/infra
git add playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml
git commit -m "feat(malcolm): add system-aw-deploy role"
```

---

## Task 5: Create chezmoi modify script (dotfiles repo)

**Files:**
- Create: `~/.local/share/chezmoi/modify_dot_claude.json` (executable)

This file lives in the dotfiles git repo, not the infra repo. It runs on any machine
where `chezmoi apply` is invoked, and conditionally merges the `aw-deploy` MCP server
entry into `~/.claude.json` based on whether the binary is present.

- [ ] **Step 1: Write the modify script**

Create `~/.local/share/chezmoi/modify_dot_claude.json`:

```python
#!/usr/bin/env python3
"""Chezmoi modify script: merge aw-deploy MCP server entry into ~/.claude.json."""
import json
import sys
from pathlib import Path

BINARY = "/usr/local/bin/aw-deploy-mcp"
SERVER_NAME = "aw-deploy"
SERVER_CONFIG = {
    "type": "stdio",
    "command": BINARY,
}

content = sys.stdin.read()
try:
    data = json.loads(content) if content.strip() else {}
except json.JSONDecodeError:
    sys.stdout.write(content)
    sys.exit(1)

servers = data.setdefault("mcpServers", {})

if Path(BINARY).exists():
    servers[SERVER_NAME] = SERVER_CONFIG
else:
    servers.pop(SERVER_NAME, None)

print(json.dumps(data, indent=2))
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x ~/.local/share/chezmoi/modify_dot_claude.json
```

- [ ] **Step 3: Commit to the dotfiles repo**

```bash
cd ~/.local/share/chezmoi
git add modify_dot_claude.json
git commit -m "feat: merge aw-deploy MCP registration into ~/.claude.json"
git push
```

- [ ] **Step 4: Run `chezmoi apply` on the laptop**

At this point the binary is NOT yet installed on the laptop (it's unmanaged). Apply should run cleanly and leave `~/.claude.json` unchanged (no binary = no registration).

```bash
chezmoi apply --verbose 2>&1 | grep -E "claude|aw-deploy|modify"
```

Expected: modify script runs, binary not found, no entry added (no error).

- [ ] **Step 5: Install binaries manually on the laptop**

The laptop is not Ansible-managed. Run these commands once:

```bash
# Create venv
sudo mkdir -p /opt/awfulwoman/aw-deploy
sudo chown $(whoami):staff /opt/awfulwoman/aw-deploy
uv venv /opt/awfulwoman/aw-deploy/venv
VIRTUAL_ENV=/opt/awfulwoman/aw-deploy/venv uv pip install mcp

# Install CLI (stdlib only, no venv needed)
sudo cp ~/Code/awfulwoman/infra/roles/system-aw-deploy/files/aw-deploy /usr/local/bin/aw-deploy
sudo chmod 755 /usr/local/bin/aw-deploy

# Render and install MCP shim with correct venv path
# (The .j2 template has one variable: system_aw_deploy_venv_dir)
# Render it manually by substituting the venv path:
sed 's|{{ system_aw_deploy_venv_dir }}|/opt/awfulwoman/aw-deploy/venv|g' \
  ~/Code/awfulwoman/infra/roles/system-aw-deploy/templates/aw-deploy-mcp.j2 \
  | sudo tee /usr/local/bin/aw-deploy-mcp > /dev/null
sudo chmod 755 /usr/local/bin/aw-deploy-mcp
```

- [ ] **Step 6: Verify CLI works on the laptop**

```bash
aw-deploy list | head -5
aw-deploy hosts | head -10
```

Expected: playbook list and inventory tree printed.

- [ ] **Step 7: Run `chezmoi apply` again — now the binary exists**

```bash
chezmoi apply
```

Expected: `~/.claude.json` is updated. Verify:

```bash
python3 -c "import json; d=json.load(open('/Users/charlie/.claude.json')); print(json.dumps(d.get('mcpServers', {}).get('aw-deploy'), indent=2))"
```

Expected output:
```json
{
  "type": "stdio",
  "command": "/usr/local/bin/aw-deploy-mcp"
}
```

---

## Task 6: Verify end-to-end on both machines

- [ ] **Step 1: Verify MCP shim syntax and imports on the laptop**

The shim uses async MCP protocol and won't respond to a piped JSON message — verify it's syntactically correct and all imports resolve:

```bash
/opt/awfulwoman/aw-deploy/venv/bin/python3 -c "
import ast, sys
with open('/usr/local/bin/aw-deploy-mcp') as f:
    lines = f.readlines()
ast.parse(''.join(lines[1:]))  # skip shebang
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
print('OK: syntax valid, imports resolved')
"
```

Expected: `OK: syntax valid, imports resolved`

- [ ] **Step 2: Verify MCP shim on Malcolm**

```bash
ssh malcolm '/opt/awfulwoman/aw-deploy/venv/bin/python3 -c "
import ast
with open(\"/usr/local/bin/aw-deploy-mcp\") as f:
    lines = f.readlines()
ast.parse(\"\".join(lines[1:]))
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
print(\"OK: syntax valid, imports resolved\")
"'
```

Expected: `OK: syntax valid, imports resolved`

- [ ] **Step 3: Run a real playbook in check mode via the CLI**

On the laptop (or Malcolm), run a real playbook in check mode to verify vault password, inventory, and SSH keys are all wired up:

```bash
aw-deploy run playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml \
  --tags system-aw-deploy --check
```

Expected: ansible-playbook check mode output, exit 0, log written to `~/.local/state/aw-deploy/runs/`.

- [ ] **Step 4: Verify run log was written**

```bash
aw-deploy logs --tail 1
```

Expected: log content from the check-mode run above.

- [ ] **Step 5: Open a new Claude Code session in a different project and confirm the tool is visible**

```bash
cd ~/Code/awfulwoman/personal-site
claude
```

In the session, check the MCP tools are available. The `aw-deploy` server should appear in the tools list. Test with a `list_playbooks` call to verify the connection without running anything.

---

## Task 7: Run `chezmoi apply` on Malcolm

After Malcolm has the binary installed (via the Ansible role in Task 4), chezmoi also needs to run there to register the MCP server in Malcolm's `~/.claude.json`.

- [ ] **Step 1: Pull dotfiles on Malcolm and apply**

```bash
ssh malcolm 'chezmoi update'
```

`chezmoi update` pulls from the remote dotfiles repo and applies. Expected: `~/.claude.json` on Malcolm now has the `aw-deploy` entry.

- [ ] **Step 2: Verify on Malcolm**

```bash
ssh malcolm 'python3 -c "import json; d=json.load(open(\"$HOME/.claude.json\")); print(d.get(\"mcpServers\", {}).get(\"aw-deploy\"))"'
```

Expected: `{'type': 'stdio', 'command': '/usr/local/bin/aw-deploy-mcp'}`
