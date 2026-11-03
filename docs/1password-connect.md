# 1Password Connect

1Password Connect is a self-hosted server. It syncs a 1Password vault locally and exposes secrets through a REST API. Ansible Vault no longer needs to store these secrets for day-to-day use. Secrets stay in 1Password. Ansible fetches them at playbook runtime with short-lived, rotatable tokens.

The Connect server runs on `minipc-8gb-camina`. Traefik exposes it at `https://connect.{{ domainname_infra }}`.

## Architecture

Two containers collaborate:

| Container | Role |
| --- | --- |
| `op-connect-api` | REST API server. Receives requests with a bearer token and serves secrets from the local SQLite database. Exposed via Traefik. |
| `op-connect-sync` | Background sync process. Authenticates with `my.1password.com` and continuously replicates vault data into the shared database. |

Both containers share:
- A named Docker volume (`op-connect-data`) for the SQLite database.
- A read-only bind mount of `1password-credentials.json` from `{{ composition_config }}`.
- The same Docker bridge network, so the gossip protocol between them can function.

## Initial Setup

### 1. Generate credentials in 1Password

Use the `op` CLI to create the Connect server and generate credentials. This produces `1password-credentials.json` in the current directory.

```bash
# Create the Connect server and grant it access to the Infra vault
op connect server create "Home Infra" --vaults Infra

# Issue the read access token for Ansible to use (grant read only; see Write token below for the separate write token)
op connect token create "ansible" --server "Home Infra" --vault Infra
```

Save the token output. The token appears only once. Store the **read** token as `vault_onepassword_connect_infra_token_read` (see [Using Secrets in Ansible](#using-secrets-in-ansible)).

### 2. Store credentials in Ansible Vault

The credentials file contains a cryptographic hash (`verifier.localHash`) that must match the file's exact bytes. Base64-encode the file before encrypting to preserve exact bytes through Ansible's templating:

```bash
ansible-vault encrypt_string "$(base64 < 1password-credentials.json)" \
  --name 'vault_onepassword_connect_credentials'
```

Paste the output into `inventory/group_vars/infra/vault_onepassword_connect.yaml`.

> **Important:** Do not use `ansible.builtin.template` to deploy this file. The `end-of-file-fixer` pre-commit hook adds a trailing newline. This breaks the hash. The role uses `ansible.builtin.copy` with `content: "{{ vault_onepassword_connect_credentials | b64decode }}"` to write the exact original bytes.

### 3. Deploy

```bash
ansible-playbook playbooks/hosts/minipc-8gb-camina/core.yaml \
  --tags composition -e target_composition=1password-connect
```

### 4. Verify

```bash
curl https://connect.{{ domainname_infra }}/health
curl -H "Authorization: Bearer <token>" https://connect.{{ domainname_infra }}/v1/vaults
```

The first authenticated request starts the sync. Once the initial sync completes, later requests return vault data.

## Using Secrets in Ansible

The `onepassword_connect` lookup (`plugins/lookup/`) reads one field of one item by its **title**. It talks to Connect over HTTPS with Python's standard library, so it needs no `op` CLI and no extra packages, and it runs the same on camina, in the Semaphore container and on malcolm.

```yaml
github_stars_token: "{{ lookup('onepassword_connect', 'External - GitHub', 'stars token') }}"
```

- Arguments: the item title, then the field. The field matches a **label** first, then a field **id** (a Login or Server item's built-ins are `username` and `password`).
- Optional `vault='...'` (name or ID) instead of the Infra vault.
- Exactly one item must match the title. A missing item, missing field, duplicate title, empty value, HTTP error or unreachable Connect **raises**, naming the title and field and never the value. There is no `default=`: a secret that cannot be read must stop the run.
- Each item is fetched once per run.
- Fields only. Multi-line values and documents are not supported yet.

Settings come from Ansible variables, not the environment (`group_vars/infra/core.yaml`):

| Variable | Value |
| --- | --- |
| `onepassword_connect_host` | `https://connect.{{ domainname_infra }}`, the Traefik URL, from every host |
| `onepassword_connect_token` | `vault_onepassword_connect_infra_token_read`, the **read** token, kept in Ansible Vault as a bootstrap credential |
| `onepassword_connect_vault_id` | The Infra vault |

Each host's `core.yaml` starts with the `preflight-onepassword` role. It stops the run, with a clear message, if the token is empty or `/health` does not answer.

### Write token

Creating or changing items needs a separate **write** token, scoped to the Infra vault only. It is **never** stored in Ansible Vault, Semaphore or the repo. Set it only in the shell that runs the provisioning, and close the shell afterwards:

```bash
export OP_CONNECT_TOKEN_WRITE='<token>'
```

## Groups, titles, tags and categories

Every item in the Infra vault belongs to one group. The group sets the title prefix, the tag and the 1Password category. A category cannot be changed after an item is created.

| Group | Title prefix | Tag | Category |
| --- | --- | --- | --- |
| App | `App - <App>` | `app` | Secure Note |
| Login | `Infra - <App>` | `login` | Login |
| Host | `Host - <Host>` | `host` | Server |
| Hardware | `Hardware - <Device>` | `hardware` | Secure Note |
| External | `External - <Provider>` | `external` | Secure Note |

Items that a lookup reads also carry the tag `ansible`. Only Login items autofill. Each secret is a field on the item, labelled in lowercase words (`stars token`, `storage box password`). The full rules, and the item and label for every migrated variable, are in the [spec](https://github.com/awfulwoman/meta/blob/main/specs/infra/01-ansible-vault-to-1password-connect.md) and its [appendix](https://github.com/awfulwoman/meta/blob/main/specs/infra/01-appendix-vault-inventory.md).

## Audit

```bash
ansible-playbook playbooks/utility/audit-secrets.yaml
```

It prints names only, never values, and fails if it finds errors:

- every title a `lookup('onepassword_connect', ...)` names exists exactly once, has that field, and is tagged `ansible`;
- every field with a value on an `ansible`-tagged item has a consumer: a lookup that names it, or its label as a whole word somewhere in `roles/`, `playbooks/`, `inventory/` or `scripts/` (built-in `username` and `password` need an explicit lookup);
- every item has exactly one group tag and the matching title prefix, and no duplicate titles.

Category and stray-tag findings are warnings. The checks live in `plugins/lookup/op_audit.py`, with tests in `tests/test_op_audit.py`.

## Bootstrap Paradox

The credentials file that the Connect server needs to run cannot itself be stored in Connect, because the server is not running yet. Ansible Vault stores it instead, and the role deploys it at provisioning time. This is intentional. Once the server runs, other secrets can migrate to Connect.
