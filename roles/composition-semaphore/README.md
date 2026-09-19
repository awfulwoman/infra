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

Semaphore configuration (projects, keys, templates) is done in the UI and is
not managed by this role. For this repo, a project needs:

- **Repository**: `git@github.com:awfulwoman/infra.git`, with an SSH key that
  can read it.
- **SSH key** for the fleet, stored as an access key.
- **Vault password** for the `beanpod` identity, stored as an access key.
- **Galaxy dependencies**: Semaphore only installs `roles/requirements.yml`
  and `collections/requirements.yml`. This repo keeps them in
  `meta/requirements.yaml`, so they need installing some other way.
