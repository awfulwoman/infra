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

Projects, keys and templates live in Semaphore's database, not in this
role. The `infra` project has:

| Item | Value |
|------|-------|
| Repository | `https://github.com/awfulwoman/infra.git`, `main`, no key (public) |
| Inventory | `inventory/` from the repository: the whole directory, as `ansible.cfg` loads it. `hosts-unmanaged.yaml` defines groups bertha's dhcpd and named templates need |
| Access key | `fleet-ssh (camina)`: camina's `~/.ssh/id_ed25519`, authorized fleet-wide via the GitHub key updater |
| Templates | `<host>: core` for each `playbooks/hosts/*/core.yaml`. Arguments can be overridden per run, e.g. `["--tags", "composition", "-e", "target_composition=reverseproxy"]` |

### Nightly schedules

Europe/Berlin, staggered so runs do not overlap much:

| Time | Template |
|------|----------|
| 01:30 | `minipc-8gb-camina: galaxy refresh` (`--tags ansible-core`) |
| 02:00 | `minipc-8gb-camina: core` |
| 02:20 | `server-64gb-storage: core` |
| 02:40 | `minipc-8gb-homebrain: core` |
| 03:00 | `minipc-8gb-agatha: core` |
| 03:20 | `vps-hetzner-public01: core` |
| 03:40 | `router-4gb-bertha: core` |
| 04:30 | `semaphore heartbeat` (`playbooks/utility/semaphore-heartbeat.yaml`) |

The heartbeat pings the healthchecks.io check "Semaphore scheduled runs
(camina)". If the scheduler stops, the pings stop and healthchecks.io
alerts. Peekaping watches `semaphore.<domain>` itself.

A scheduled run deploys whatever is on `main`. Before pushing a change that
should be applied by hand first (a host renumber from the LAN address plan,
say), pause that host's schedule in the UI.

`--check` is not reliable: many read-only `command` tasks are skipped in
check mode, and the facts parsed from them are then missing.

Not available in the image: Terraform (`infra-*` roles).
