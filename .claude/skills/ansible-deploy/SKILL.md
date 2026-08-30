---
name: ansible-deploy
description: Use when deploying Ansible playbooks to hosts or groups, selecting
  the right playbook file, or targeting specific roles or role types with tags.
---

- `core.yaml` (if present) is the default playbook for a host or group
- Read the `name` key of a playbook to determine relevancy to the task at hand
- Each host or group can have multiple task-specific playbooks
- Deploy all roles of a certain type using a tag based on the relevant prefix (e.g. `composition` for composition-* roles)
- Roles listed statically in a playbook carry their own name as a tag, allowing fine-grained deployment
- **Exception: most composition-* roles have no tag of their own** — see "Deploying a single composition" below
- `aw-deploy repo <github-url>` prints the exact deploy command for whichever roles reference that repo, composition form included. Use it rather than guessing a tag.

## Execution

Check for `aw-deploy` first — it provides concurrency protection, run logging, and correct PATH for subprocesses:

```bash
command -v aw-deploy >/dev/null 2>&1
```

**If available**, use `aw-deploy run`:
```bash
aw-deploy run <playbook> [--tags <tags>] [--limit <host>] [--extra-vars KEY=VALUE] [--check]
```

`aw-deploy run` accepts only those flags. It has no `-e` short form — `-e foo=bar` fails with `unrecognized arguments`. Use `--extra-vars foo=bar`, repeated once per variable.

**If not available**, fall back to `ansible-playbook` directly:
```bash
ansible-playbook <playbook> [--tags <tags>] [--limit <host>] [--check]
```

## Deploying a single composition

Most hosts deploy compositions data-driven: `system-compositions` loops over the host's
`compositions:` list and `include_role`s each `composition-*` in turn. Those included roles
inherit only the `composition` tag from the playbook entry — **there is no `composition-<name>`
tag**. Target one composition with `target_composition` instead:

```bash
aw-deploy run playbooks/hosts/<host>/core.yaml --tags composition \
  --extra-vars target_composition=<name>
```

`target_composition` also accepts a comma-separated list. It reads `compositions:` directly,
so nothing has to be kept in sync by hand.

A few composition roles *are* listed statically in a playbook (e.g. `composition-reverseproxy`
and `composition-zfs-api` on albion and the zfs_backup groups) and do carry their own tag.
Check the playbook before assuming which form applies.

**`--tags composition-<name>` is not an error — it silently matches nothing.** The run exits 0
with a recap of `ok=1 changed=0` and `Gathering Facts` as the only task. Always read the recap
task count, not just the exit code.

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

**Stop the Monitor** as soon as a terminal signal (`PLAY RECAP`, `fatal`, `ERROR`) is seen — the Monitor has no built-in stop condition and will tail indefinitely if not cancelled.

**Expect no live progress from a short run.** The background output file has been observed
sitting at 0 bytes for the whole of a multi-minute deploy, then filling in at once on exit —
so the Monitor fires every event together with the recap at the end. aw-deploy's own run log
at `~/.local/state/aw-deploy/runs/<timestamp>-<slug>.log` is worse: it is written without
flushing, so it stays empty until the run finishes and is no use for tailing either.

A silent tail is therefore **not** evidence of a stalled deploy, and an empty run log is not
evidence of a failed one. Treat the completion notification as the signal, and SSH the host
if you actually need to see what is happening mid-run.

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

## DNS registration for new compositions

Public DNS (`*.ewwww.eu` CNAMEs) is managed by the `infra-named` role on `router-4gb-bertha`, which writes records to Hetzner DNS. CNAMEs are derived automatically from the `compositions:` list in each host's `host_vars`. After adding a new composition to that list, register its subdomain by running:

```bash
aw-deploy run playbooks/hosts/router-4gb-bertha/core.yaml --tags infra-named
```

This is needed whenever a composition is first added — deploying the composition itself does not register DNS.

## Common failure patterns in this repo

**`ansible.builtin.copy` leaves stale files on the remote** — the `copy` module only adds/updates, never deletes. If a large directory (e.g. `.venv`) gets copied once, it persists and causes future deploys to hang while Ansible checksums thousands of files. Use `ansible.posix.synchronize` with `delete: true` and `rsync_opts` excludes for directory syncs.

**`ansible.builtin.uri` runs on the control node** — to call `localhost:PORT` on the target host (e.g. a sidecar API), add `delegate_to: "{{ inventory_hostname }}"`. Without it, Ansible calls the external URL from the Mac, which may fail due to TLS cert race after DNS registration.

**`ansible.posix.synchronize` without `delegate_to`** — correctly pushes from the control node to the target via SSH. Adding `delegate_to: inventory_hostname` makes rsync run on the target using control-node paths, which fails immediately.

**New subdomain + HTTPS immediately** — after `network-register-subdomain`, Traefik needs 30–120s to complete the ACME challenge. Don't call the HTTPS URL in the same play; use `delegate_to` + `http://localhost:PORT` instead.

**Alpine images and `/dev/tcp`** — Alpine's busybox `sh` does not support `/dev/tcp`. Any role that runs on `louislam/uptime-kuma` or other Alpine-based images must use `bash -c 'echo > /dev/tcp/...'` in healthchecks (bash is present). See `.claude/rules/docker-healthcheck.md`.

**Socket.io / slow-connecting APIs** — lazy-connecting sidecar services (e.g. uptime-kuma-api) may take 60s+ to authenticate on first request. Set `timeout: 120` on any `uri` task that triggers the first connection.
