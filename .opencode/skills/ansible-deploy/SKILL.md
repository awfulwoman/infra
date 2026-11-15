---
name: ansible-deploy
description: Use when deploying Ansible playbooks to hosts or groups, selecting
  the right playbook file, targeting specific roles or role types with tags,
  running a deploy through Semaphore on camina, or reading the result of one.
---

Deploys run on **camina**, as Ansible Semaphore tasks (`composition-semaphore`).
There is no `aw-deploy` any more: it was removed along with Semaphore being the
only wrapper worth keeping.

- `core.yaml` (if present) is the default playbook for a host or group
- Read the `name` key of a playbook to determine relevancy to the task at hand
- Each host or group can have multiple task-specific playbooks
- Deploy all roles of a certain type using a tag based on the relevant prefix (e.g. `composition` for composition-* roles)
- Roles listed statically in a playbook carry their own name as a tag, allowing fine-grained deployment
- **Exception: most composition-* roles have no tag of their own** — see "Deploying a single composition" below

## Which template

Every template pins its playbook. What can be chosen at run time is the host,
the arguments (`--tags`, `--limit`, `-e`) and, for the local pair, nothing else.

| Template | Repository | Use for |
|----------|------------|---------|
| `<host>: core` | GitHub `main` | What the nightly runs do. Deploying what is pushed. |
| `<host>: core (local)` | the checkout on camina | Trying a change before pushing: uncommitted work, no push round-trip. |
| `group: <path>` | GitHub `main` | Group playbooks (`groups/ubuntu/bootstrap.yaml`, etc.) |
| `semaphore heartbeat` | GitHub `main` | Checking scheduled runs still happen. Harmless. |

**There is deliberately no template that takes the playbook as an override.** A
deploy runs with the vault unlocked, so an arbitrary playbook is a way to print
any secret into a run log, and run logs are readable over the gateway API. Do
not add one; see `roles/composition-semaphore/README.md`.

Consequences worth remembering:

- **A scheduled run is `main`.** Anything applied by hand and left unpushed is
  reverted that night. Push it, or pause that host's schedule with
  `active: false` in `composition_semaphore_schedules` and deploy the semaphore
  composition.
- **`(local)` templates are never scheduled.** An assert in `tasks/project.yaml`
  fails the role deploy if a schedule names one.
- **One run at a time** (`max_parallel_tasks: 1`). An ad-hoc run queues behind
  the nightly ones rather than colliding with them.

## Running a deploy

From an agent session, use the gateway's Semaphore tools — they are the only
route that works from the sandbox, which cannot read `/opt/ansible/.vaultpassword`:

1. `workflows_search(project_id=1, query="<host>")` — find the template id.
2. `workflows_run(project_id=1, workflow_id=<id>, arguments='["--tags","composition","-e","target_composition=<name>"]')`
   `arguments` is a **JSON array string**, not a shell string. `limit` is a
   separate parameter.
3. `pipelines_list(project_id, workflow_id)` → newest run id.
4. `jobs_logs(project_id, job_id)` to read it; `jobs_describe` for status and
   arguments. Repeat until the status leaves `running`.

Do not poll on a fixed short sleep for a composition deploy: Docker Compose
builds and health checks take 3–5 minutes, sometimes much longer on a first
build. Read the log when the status changes, and in the meantime check the host
directly if you need to see something mid-run:

```ssh
ssh <host> 'docker ps --filter name=<service> --format "table {{.Names}}\t{{.Status}}"'
ssh <host> 'docker logs <container> --tail 20 2>&1'
```

`jobs_logs` masks secrets (vault/PEM blobs, and `key: value` pairs whose key
names a secret). That is best-effort: do not rely on it to make a playbook that
prints secrets safe.

### Stopping a run

`pipelines_stop(project_id=1, pipeline_id=<task id>, force=true)`. The most
common cause of a run that never ends is a container whose healthcheck never
passes while a dependent service waits on it — fix the healthcheck, then
redeploy. There is no lock file to clear; Semaphore tracks the task.

## Running a playbook with no template

Utility playbooks, one-offs and tests have no template by design. Run them from
a **shell on camina**, as the `awful` user — not from an agent sandbox, which
cannot read the vault password:

```bash
cd ~/Code/awfulwoman/infra
ansible-playbook playbooks/utility/<name>.yaml [--tags <tags>] [--limit <host>] [-e KEY=VALUE]
```

`ansible.cfg` supplies the inventory, `roles_path`
(`/opt/ansible/galaxy/roles`) and `vault_password_file`
(`/opt/ansible/.vaultpassword`), so no flags are needed for those. `-e` short
form works here, unlike the old `aw-deploy run`.

### Deploying Semaphore itself

Do **not** run camina's own `core` template from Semaphore to change this role:
recreating the container kills the task that is running the play. From a shell
on camina instead:

```bash
ansible-playbook playbooks/hosts/minipc-8gb-camina/core.yaml \
  --tags composition -e target_composition=semaphore
```

## Deploying a single composition

Most hosts deploy compositions data-driven: `system-compositions` loops over the host's
`compositions:` list and `include_role`s each `composition-*` in turn. Those included roles
inherit only the `composition` tag from the playbook entry — **there is no `composition-<name>`
tag**. Target one composition with `target_composition` instead:

```
arguments: ["--tags", "composition", "-e", "target_composition=<name>"]
```

`target_composition` also accepts a comma-separated list. It reads `compositions:` directly,
so nothing has to be kept in sync by hand.

A few composition roles *are* listed statically in a playbook (e.g. `composition-reverseproxy`
and `composition-zfs-api` on albion and the zfs_backup groups) and do carry their own tag.
Check the playbook before assuming which form applies.

**`--tags composition-<name>` is not an error — it silently matches nothing.** The run
exits 0 with a recap of `ok=1 changed=0` and `Gathering Facts` as the only task. Always read
the recap task count, not just the exit code.

`--check` is unreliable in this repo: many read-only `command` tasks are skipped in check
mode, and the facts parsed from them are then missing.

## DNS registration for new compositions

Public DNS (`*.<domain>` CNAMEs) is managed by the `infra-named` role on `router-4gb-bertha`, which writes records to Hetzner DNS. CNAMEs are derived automatically from the `compositions:` list in each host's `host_vars`. After adding a new composition to that list, register its subdomain by running the `router-4gb-bertha: core` template restricted to that tag — `infra-named` is a statically listed role, so it carries its own tag:

```
arguments: ["--tags", "infra-named"]
```

This is needed whenever a composition is first added — deploying the composition itself does not register DNS.

## Common failure patterns in this repo

**`ansible.builtin.copy` leaves stale files on the remote** — the `copy` module only adds/updates, never deletes. If a large directory (e.g. `.venv`) gets copied once, it persists and causes future deploys to hang while Ansible checksums thousands of files. Use `ansible.posix.synchronize` with `delete: true` and `rsync_opts` excludes for directory syncs.

**`ansible.builtin.uri` runs on the control node** — to call `localhost:PORT` on the target host (e.g. a sidecar API), add `delegate_to: "{{ inventory_hostname }}"`. Without it, Ansible calls the external URL from camina, which may fail due to a TLS cert race after DNS registration.

**`ansible.posix.synchronize` without `delegate_to`** — correctly pushes from the control node to the target via SSH. Adding `delegate_to: inventory_hostname` makes rsync run on the target using control-node paths, which fails immediately.

**New subdomain + HTTPS immediately** — after `network-register-subdomain`, Traefik needs 30–120s to complete the ACME challenge. Don't call the HTTPS URL in the same play; use `delegate_to` + `http://localhost:PORT` instead.

**A pinned upstream version can vanish** — a PyPI release can be yanked, and a Docker tag can be rebuilt against a newer base. A nightly run then fails on a `docker compose build` that worked last week. The build log names the failing `RUN` line; check the release still exists and that the base image is the one the role comments say it is deliberately pinned to.

**Alpine images and `/dev/tcp`** — Alpine's busybox `sh` does not support `/dev/tcp`. Any role that runs on `louislam/uptime-kuma` or other Alpine-based images must use `bash -c 'echo > /dev/tcp/...'` in healthchecks (bash is present). See `.opencode/rules/docker-healthcheck.md`.

**Socket.io / slow-connecting APIs** — lazy-connecting sidecar services (e.g. uptime-kuma-api) may take 60s+ to authenticate on first request. Set `timeout: 120` on any `uri` task that triggers the first connection.
