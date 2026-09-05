# System Git

Configures global git settings for the Ansible user. Sets identity, pull behaviour, and default branch name via the `community.general.git_config` module.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `system_git_user_name` | `Charlie O'Hara` | Git `user.name` |
| `system_git_user_email` | `github@<personal_domain>` | Git `user.email` (resolved from vault) |
| `system_git_pull_rebase` | `true` | Sets `pull.rebase` — avoids merge commits on pull |
| `system_git_init_defaultbranch` | `main` | Sets `init.defaultBranch` |

## Design Notes

The role applies all settings at global scope (`~/.gitconfig` for the Ansible user). The email address comes from a vaulted personal domain variable rather than a hardcoded value, so it stays correct if the domain changes.
