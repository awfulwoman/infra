---
name: ansible-deploy
description: Use when deploying Ansible playbooks to hosts or groups, selecting
  the right playbook file, or targeting specific roles or role types with tags.
---

- `core.yaml` (if present) is the default playbook for a host or group
- Read the `name` key of a playbook to determine relevancy to the task at hand
- Each host or group can have multiple task-specific playbooks
- Deploy all roles of a certain type using a tag based on the relevant prefix (e.g. `compositions` for composition-* roles)
- Each role has its name as a unique tag, allowing fine-grained deployment

## Execution

Check for `aw-deploy` first — it provides concurrency protection, run logging, and correct PATH for subprocesses:

```bash
command -v aw-deploy >/dev/null 2>&1
```

**If available**, use `aw-deploy run`:
```bash
aw-deploy run <playbook> [--tags <tags>] [--limit <host>] [--check]
```

**If not available**, fall back to `ansible-playbook` directly:
```bash
ansible-playbook <playbook> [--tags <tags>] [--limit <host>] [--check]
```

## Running deploys

Deploys that include Docker Compose steps (building images, waiting for health checks) can take 3–5+ minutes. Always run in background and use Monitor to watch progress:

```bash
# Run in background (use run_in_background: true in Bash tool)
aw-deploy run <playbook> --tags <tag>
```

Watch for key events with Monitor, covering both success and failure signals:
```bash
tail -f /path/to/output | grep --line-buffered -E "changed:|failed:|PLAY RECAP|fatal|ERROR|<role-specific summary>"
```

Use SSH to proactively check the host if progress stalls — don't wait for a timeout:
```bash
ssh <host> 'docker ps --filter name=<service> --format "table {{.Names}}\t{{.Status}}"'
ssh <host> 'docker logs <container> --tail 20 2>&1'
```

## Stuck deploy recovery

aw-deploy holds a lock at `~/.local/state/aw-deploy/run.lock`. If a deploy hangs (e.g. Docker Compose waiting for a permanently-unhealthy container), it holds the lock forever.

To recover:
```bash
# Find and kill the stuck process
lsof ~/.local/state/aw-deploy/run.lock 2>/dev/null | awk 'NR>1 {print $2}' | xargs kill
# Clear the lock
rm -f ~/.local/state/aw-deploy/run.lock
```

The most common cause of a stuck deploy is a container with a failing healthcheck that a dependent service is waiting on. Fix the healthcheck before redeploying.

## Common failure patterns in this repo

**`ansible.builtin.copy` leaves stale files on the remote** — the `copy` module only adds/updates, never deletes. If a large directory (e.g. `.venv`) gets copied once, it persists and causes future deploys to hang while Ansible checksums thousands of files. Use `ansible.posix.synchronize` with `delete: true` and `rsync_opts` excludes for directory syncs.

**`ansible.builtin.uri` runs on the control node** — to call `localhost:PORT` on the target host (e.g. a sidecar API), add `delegate_to: "{{ inventory_hostname }}"`. Without it, Ansible calls the external URL from the Mac, which may fail due to TLS cert race after DNS registration.

**`ansible.posix.synchronize` without `delegate_to`** — correctly pushes from the control node to the target via SSH. Adding `delegate_to: inventory_hostname` makes rsync run on the target using control-node paths, which fails immediately.

**New subdomain + HTTPS immediately** — after `network-register-subdomain`, Traefik needs 30–120s to complete the ACME challenge. Don't call the HTTPS URL in the same play; use `delegate_to` + `http://localhost:PORT` instead.

**Alpine images and `/dev/tcp`** — Alpine's busybox `sh` does not support `/dev/tcp`. Any role that runs on `louislam/uptime-kuma` or other Alpine-based images must use `bash -c 'echo > /dev/tcp/...'` in healthchecks (bash is present). See `.claude/rules/docker-healthcheck.md`.

**Socket.io / slow-connecting APIs** — lazy-connecting sidecar services (e.g. uptime-kuma-api) may take 60s+ to authenticate on first request. Set `timeout: 120` on any `uri` task that triggers the first connection.
