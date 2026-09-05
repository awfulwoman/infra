# System SSH Key

If an ed25519 SSH keypair does not already exist for the Ansible connecting user, this role generates one on the remote host.

This gives a host its own SSH identity. The host needs this identity to authenticate to other systems with its own key. For example, the host can push to a Git remote, connect to a backup target, or connect by SSH between home servers.

## Design Notes

- The role has no variables. It always places the key at `~/.ssh/id_ed25519` for the `ansible_user`.
- The role sets the key comment to `user@hostname`, for easy identification across hosts.
- The `community.crypto.openssh_keypair` module is idempotent and will not overwrite an existing key.
- Key type is hardcoded to ed25519.
