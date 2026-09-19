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
| `vault_composition_semaphore_admin_password` | Initial `admin` password |
| `vault_composition_semaphore_access_key_encryption` | Encrypts stored access keys. Base64 of 32 random bytes. **Do not rotate**: changing it makes every stored key unreadable |

Read the admin password without printing it to a shared log:

```bash
ansible localhost -m debug -a "var=vault_composition_semaphore_admin_password" \
  -e @inventory/group_vars/infra/vault_composition_semaphore.yaml
```

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
| Repository | `https://github.com/awfulwoman/infra.git`, `main`, Semaphore's built-in `None` key (the repo is public) |
| Inventory | `inventory/` from the repository: the whole directory, as `ansible.cfg` loads it. `hosts-unmanaged.yaml` defines groups bertha's dhcpd and named templates need |
| Templates | `<host>: core` for every `playbooks/hosts/*/core.yaml`, found on the controller at run time, plus `composition_semaphore_templates_extra`. All merged over `composition_semaphore_template_defaults` |
| Schedules | `composition_semaphore_schedules`, set in camina's host_vars |

Templates allow per-run argument overrides, e.g.
`["--tags", "composition", "-e", "target_composition=reverseproxy"]` or
`["--limit", "server-64gb-storage"]`.

Left out of `composition_semaphore_templates_extra` on purpose, with reasons
in `defaults/main.yaml`: `groups/kubernetes`, `groups/personal`,
`groups/infra/reboot-all`, and utility playbooks that write files into the
checkout.

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
