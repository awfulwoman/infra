# User Site Deployment

Creates a dedicated system user to deploy static website content to the host over SSH.

The role creates the user with a fixed UID (1100) and no home directory. It authorizes the user with a specific public key from Ansible Vault. This lets a CI/CD pipeline or local build tool send files to the server with `rsync` or `scp`. It does not need a full privileged account to do this.

## Required Vault Variables

| Variable | Description |
|---|---|
| `vault_sitedeployer_user` | Username for the deployment account |
| `vault_sitedeployer_publickey` | SSH public key authorised for this user |

## Design Notes

- If either vault variable is undefined, the role does nothing. This makes it safe to include in playbooks where not all hosts need a deployment user.
- The user gets bash as its shell to support `rsync`-over-SSH workflows.
- A commented-out `key_options` line in the tasks hints at a future improvement. It can restrict the key to allow only `rsync` commands, with `restrict,command="rsync"`.
- UID 1100 is hardcoded to keep the account's identity stable across rebuilds.
