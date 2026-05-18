# 1Password Connect

1Password Connect is a self-hosted server that syncs a 1Password vault locally and exposes secrets via a REST API. It replaces the need to embed secrets directly in Ansible Vault for day-to-day use — secrets live in 1Password and are fetched at playbook runtime using short-lived, rotatable tokens.

The Connect server is deployed to `raspberry-pi4-4gb-randolph` and exposed at `https://connect.{{ domainname_infra }}` via Traefik.

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

# Issue an access token for Ansible to use
op connect token create "ansible" --server "Home Infra" --vault Infra
```

Save the token output — it is shown only once. Store it as a vault-encrypted variable (see [Using Secrets in Ansible](#using-secrets-in-ansible)).

### 2. Store credentials in Ansible Vault

The credentials file contains a cryptographic hash (`verifier.localHash`) that must match the file's exact bytes. Base64-encode the file before encrypting to preserve exact bytes through Ansible's templating:

```bash
ansible-vault encrypt_string "$(base64 < 1password-credentials.json)" \
  --name 'vault_onepassword_connect_credentials'
```

Paste the output into `inventory/group_vars/infra/vault_onepassword_connect.yaml`.

> **Important:** Do not use `ansible.builtin.template` to deploy this file. The `end-of-file-fixer` pre-commit hook appends a trailing newline, which breaks the hash. The role uses `ansible.builtin.copy` with `content: "{{ vault_onepassword_connect_credentials | b64decode }}"` to write the exact original bytes.

### 3. Deploy

```bash
ansible-playbook playbooks/hosts/raspberry-pi4-4gb-randolph/core.yaml \
  --tags composition-1password-connect
```

### 4. Verify

```bash
curl https://connect.{{ domainname_infra }}/health
curl -H "Authorization: Bearer <token>" https://connect.{{ domainname_infra }}/v1/vaults
```

The first authenticated request initialises the sync. Subsequent requests return vault data once the initial sync completes.

## Using Secrets in Ansible

The `community.general.onepassword` lookup plugin retrieves secrets at playbook runtime. Set `OP_CONNECT_HOST` and `OP_CONNECT_TOKEN` as environment variables — either per-task or at the play level.

```yaml
- hosts: all
  environment:
    OP_CONNECT_HOST: "https://connect.{{ domainname_infra }}"
    OP_CONNECT_TOKEN: "{{ vault_onepassword_connect_token }}"
  tasks:
    - name: Configure service with secret from 1Password
      ansible.builtin.template:
        src: config.j2
        dest: /etc/myapp/config
      vars:
        api_key: "{{ lookup('community.general.onepassword', 'Github', field='credential', vault='Infra') }}"
```

Store `vault_onepassword_connect_token` as a vault-encrypted variable. Tokens are scoped per-vault in 1Password Connect and can be rotated independently without touching the credentials file.

## Bootstrap Paradox

The credentials file that the Connect server needs to run cannot itself be stored in Connect (the server isn't running yet). It is therefore stored in Ansible Vault and deployed by the role at provisioning time. This is intentional — once the server is running, all other secrets can migrate to Connect.
