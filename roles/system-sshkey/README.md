# System SSH Key

Generates an ed25519 SSH keypair for the Ansible connecting user on the remote host if one does not already exist.

This provisions a host's own SSH identity, needed when the host must authenticate to other systems using its own key — for example, pushing to a Git remote, connecting to a backup target, or SSHing between home servers.

## Design Notes

- No variables. The key is always placed at `~/.ssh/id_ed25519` for the `ansible_user`.
- The key comment is set to `user@hostname` for easy identification across hosts.
- The `community.crypto.openssh_keypair` module is idempotent and will not overwrite an existing key.
- Key type is hardcoded to ed25519.
