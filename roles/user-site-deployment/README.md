# User Site Deployment

Creates a dedicated system user for deploying static website content to the host over SSH.

The user is created with a fixed UID (1100) and no home directory, and is authorised with a specific public key from Ansible Vault. This allows a CI/CD pipeline or local build tool to `rsync` or `scp` files to the server without granting access to a full privileged account.

## Required Vault Variables

| Variable | Description |
|---|---|
| `vault_sitedeployer_user` | Username for the deployment account |
| `vault_sitedeployer_publickey` | SSH public key authorised for this user |

## Design Notes

- The role is a no-op if either vault variable is undefined, making it safe to include in playbooks where not all hosts need a deployment user.
- The user gets bash as its shell to support `rsync`-over-SSH workflows.
- A commented-out `key_options` line in the tasks hints at a future improvement: restricting the key to only allow `rsync` commands via `restrict,command="rsync"`.
- UID 1100 is hardcoded to keep the account's identity stable across rebuilds.
