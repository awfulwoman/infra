# System NVM

Installs [nvm](https://github.com/nvm-sh/nvm) (Node Version Manager) and a specified Node.js version for the Ansible user. Downloads and runs the official nvm install script, installs the configured Node version, and optionally sets it as the nvm default alias. All steps are idempotent — existing installations are detected and skipped.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `system_nvm_version` | `v0.40.1` | nvm version to install |
| `system_nvm_node_version` | `lts/*` | Node.js version to install; accepts nvm aliases like `lts/*` or explicit versions like `20.11.0` |
| `system_nvm_set_default` | `true` | Whether to set the installed version as the nvm default alias |

## Design Notes

nvm installs per-user into `~/.nvm`, so no `become: true` is needed. The `HOME` environment variable is explicitly passed to shell tasks because Ansible's non-interactive shell context doesn't always set it correctly, which would cause nvm to install to the wrong directory.

Node version detection uses `nvm list <version>` exit code rather than parsing output, keeping the idempotency check robust across nvm output format changes.
