# Semaphore

[Semaphore UI](https://github.com/semaphoreui/semaphore) is a web UI for
running Ansible playbooks: projects, inventories, stored keys, schedules and
run history. It runs on camina, the control node, in place of AWX (whose
only supported install is the Kubernetes operator, and whose releases are
paused).

One container, SQLite database. The image bundles its own ansible-core,
`ssh` and `git`.

## Ports

None published. Traefik routes `semaphore.<domain>` to container port 3000.

## Volumes

| Path | Container path | Purpose |
|------|----------------|---------|
| `{{ composition_config }}/config` | `/etc/semaphore` | `config.json`, generated from env on start if absent |
| `{{ composition_config }}/data` | `/var/lib/semaphore` | `database.sqlite` |

Both are owned by `composition_semaphore_uid` (1001), the image's user.
Playbook checkouts go to `/tmp/semaphore` and are not persisted.

`config.json` holds generated cookie signing keys. Deleting it and
restarting the container rotates them (logging everyone out); the
database and stored keys are unaffected.

## Secrets

In `inventory/group_vars/infra/vault_composition_semaphore.yaml`:

| Variable | Purpose |
|----------|---------|
| 1Password `Infra - Semaphore` › `password` | Initial `admin` password |
| 1Password `App - Semaphore` › `access key encryption key` | Encrypts stored access keys. Base64 of 32 random bytes. **Do not rotate**: changing it makes every stored key unreadable |

Read the admin password in 1Password, item `Infra - Semaphore`, field `password`.

The admin account is created on first start only.

## Running this repo's playbooks

The repo's `ansible.cfg` hardcodes two controller paths, so the role
provides both inside the container:

- **Galaxy content**: the host's `{{ ansible_path }}/galaxy` is mounted
  read-only at the same path. The `minipc-8gb-camina: galaxy refresh`
  template runs `ansible-core` nightly to keep it current. Semaphore's own Galaxy install only
  reads `roles/requirements.yml` and `collections/requirements.yml`, which
  this repo does not have.
- **Vault password**: the host's `ansible_vault_password_file` is copied to
  `{{ composition_config }}/vaultpassword` (0400, container UID) and mounted
  at the same path. The role therefore assumes the host is a controller with
  that file.

## Project configuration

After the container is healthy, `tasks/project.yaml` configures the `infra`
project through Semaphore's API with
[`ebdruplab.semaphoreui.project_deploy`](https://github.com/ebdruplab/ansible-collection_ebdruplab)
(pinned in `meta/requirements.yaml`). Every item is matched by name: missing
ones are created, existing ones updated. `project_deploy_variable_delete` is
false, so anything added by hand in the UI is left alone, but a declared item
edited in the UI is reset on the next run.

| Item | Source |
|------|--------|
| Project | `composition_semaphore_project_name`, `composition_semaphore_max_parallel_tasks` (1: Semaphore has no per-host lock, so one run at a time across the project) |
| Access key | `composition_semaphore_fleet_key_name`, read from `composition_semaphore_fleet_key_path` on the host. Set on creation only (`override_secret: false`) |
| Repositories | `infra`: `https://github.com/awfulwoman/infra.git`, `main`, Semaphore's built-in `None` key (the repo is public). `infra (local)`: the working checkout, mounted at the same path — see below |
| Inventories | `infra` and `infra (local)`, one per repository: `inventory/`, the whole directory, as `ansible.cfg` loads it. `hosts-unmanaged.yaml` defines groups bertha's dhcpd and named templates need |
| Templates | `<host>: core` for every `playbooks/hosts/*/core.yaml`, found on the controller at run time; `<host>: core (local)` twins that run the same playbook from the working checkout; plus `composition_semaphore_templates_extra`. All merged over `composition_semaphore_template_defaults` |
| Schedules | `composition_semaphore_schedules`, set in camina's host_vars |

Templates allow per-run argument overrides, e.g.
`["--tags", "composition", "-e", "target_composition=reverseproxy"]` or
`["--limit", "server-64gb-storage"]`.

Left out of `composition_semaphore_templates_extra` on purpose, with reasons
in `defaults/main.yaml`: `groups/kubernetes`, `groups/personal`,
`groups/infra/reboot-all`, and every utility playbook but the heartbeat.

### The working checkout

`composition_semaphore_local_repo_path`
(`/home/awful/Code/awfulwoman/infra` on camina) is the checkout this repo is
edited in on the control node — Claude Code, an editor, a shell. It is
registered as the repository `infra (local)`, with a matching inventory, and
mounted read-write into the container **at the same absolute path**, so the
repository URL and the mount cannot drift apart.

That path sits inside a `0750` home directory, which is fine: Docker creates
missing parents *inside* the container as root, mode `0755`, so what the
container's uid can traverse is its own synthetic tree, not the host's. The
host side is resolved by the daemon as root. Only the checkout's own mode
matters, and the role asserts it grants other `r-x`, naming the mode
otherwise.

It is mounted **read-write**, because the utilities that generate files in
the tree — `export-dns-records-input`, `export-service-names`, both writing
to `playbook_dir/../../scripts/` — fail on a read-only mount. Two costs come
with that: a play can dirty or damage the checkout, and the files it creates
belong to `composition_semaphore_uid`, not the ansible user (git can still
commit them; the tree just ends up with two owners). Keeping the checkout on
a snapshotted dataset, as camina's `repos` is (`policy: critical`), is the
mitigation.

A repository URL with no scheme is used in place, with no clone
(`db/Repository.go`: `RepositoryLocal` returns the path itself), so a task
against it uses the working tree exactly as it stands — uncommitted changes
included, no network. That covers trying a change before pushing it, and
deploying while GitHub is unreachable.

Nothing in Ansible updates that checkout: it is a working copy, pulled and
pushed by hand (`origin` is `git@github.com:…`, so camina's key pushes).

Which repository a task uses is fixed by its **template**, not by the task:
Semaphore has no per-task inventory override, and an inventory is bound to one
repository. So the split is explicit:

- **Every scheduled template uses `infra` (GitHub).** A nightly run deploys
  `main`, always.
- **The `<host>: core (local)` templates** carry the `(local)` pair, with the
  playbook pinned to that host's `core.yaml` and only the arguments overridable.

To deploy the working tree: start `<host>: core (local)` with arguments such as
`["--tags", "composition"]`. The project runs one task at a time
(`max_parallel_tasks: 1`), so an ad-hoc run queues behind a nightly one rather
than colliding with it.

Because the templates are declared here, a deploy of this role recreates them —
they are not UI-only changes that drift. `project_deploy` only creates and
updates, though: it never deletes, so a template that is *removed* from this
role's declarations stays in the project until deleted in the UI. The retired
`working copy` template is the case that matters — it took the playbook as a
per-task override, which is exactly the capability the pinned per-host
templates exist to remove — so delete it (and any `<host>: core` left behind by
a host that no longer exists) once, in the UI.

### Why there is no "run any playbook" template

It is tempting to have one template that takes the playbook as a per-task
override, since `local_executor.go` honours it and validates only that it stays
inside the repository. Nothing in the project does that on purpose.

A deploy runs with the vault unlocked: `ansible.cfg` points at the vault
password file the role mounts, so every task has decrypted secrets available.
A playbook of one's own choosing can therefore print any secret into the run
log — and the run log is readable over the API by the gateway's Semaphore tools
(`jobs_logs`), which is how the agent inspects failures. Keeping the playbook
pinned per host means the only things choosable at run time are a host and a
set of arguments, never the playbook.

That is a real boundary only because *no* template allows a playbook override,
so adding one back — in the UI or here — re-opens it. The gateway also masks
secrets in the logs it returns (`_redact` in `gateway/tools/semaphore.py`), as
defence in depth for the failure path: a task that dumps a secret while failing
is masked before it reaches a caller. That masking is best-effort, not the
control.

### Failure alerts

Semaphore emails on a failed task, via the mail provider `nullmailer` uses
(`mail_account_personal`), on port 587 with STARTTLS. Only failures are sent:
`sendMailAlert` is called for `TaskFailStatus` alone, so the nightly runs
stay quiet when they pass.

Three things must line up, and the role sets all three:

1. **Server**: `SEMAPHORE_EMAIL_*` in `.environment_vars`. Note the
   container writes `config.json` only when it is missing, so these settings
   live as environment variables, which override the file.
2. **Project**: the `alert` master switch.
3. **User**: Semaphore mails every project user whose `alert` flag is set,
   so `tasks/project.yaml` gives the admin account
   `composition_semaphore_admin_alert_email` and sets that flag.
   `SEMAPHORE_ADMIN_EMAIL` applies only when the account is first created.

`project_deploy` applies project settings **only when it creates the
project**, so `alert` and `max_parallel_tasks` are set separately with
`project_update` — otherwise they would silently drift on an existing
project.

Semaphore cannot report a run that never starts; that is what the heartbeat
below is for.

### Nightly schedules

Galaxy refresh first, so the core runs use current collections; the
heartbeat last. The heartbeat (`playbooks/utility/semaphore-heartbeat.yaml`)
pings the healthchecks.io check "Semaphore scheduled runs (camina)": if the
scheduler stops, healthchecks.io alerts. Peekaping watches
`semaphore.<domain>` itself.

A scheduled run deploys whatever is on `main`. Before pushing a change that
should be applied by hand first (a host renumber from the LAN address plan,
say), pause that host's schedule: add `active: false` to its entry in
`composition_semaphore_schedules` and deploy this role. Pausing in the UI
alone lasts only until camina's nightly core run redeploys this role.

`--check` is not reliable: many read-only `command` tasks are skipped in
check mode, and the facts parsed from them are then missing.

Not available in the image: Terraform (`infra-*` roles).
