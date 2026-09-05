# System NVM

This role installs [nvm](https://github.com/nvm-sh/nvm) (Node Version
Manager) and a chosen Node.js version for the Ansible user. It downloads and
runs the official nvm install script, installs the configured Node version,
and can set it as the nvm default alias. All steps are idempotent: the role
detects an existing installation and skips it.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `system_nvm_version` | `v0.40.1` | nvm version to install |
| `system_nvm_node_version` | `lts/*` | Node.js version to install. Accepts nvm aliases like `lts/*` or explicit versions like `20.11.0` |
| `system_nvm_set_default` | `true` | Whether to set the installed version as the nvm default alias |

## Design Notes

nvm installs per-user into `~/.nvm`, so the role needs no `become: true`.
The role passes the `HOME` environment variable explicitly to shell tasks.
Ansible's non-interactive shell context does not always set `HOME`
correctly, and this can cause nvm to install to the wrong directory.

Node version detection uses the exit code of `nvm list <version>`, rather
than parsing its output. This keeps the idempotency check reliable across
changes to the nvm output format.
